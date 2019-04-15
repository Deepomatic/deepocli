import logging
import traceback
import gevent
import signal
from contextlib import contextmanager
from gevent.threadpool import ThreadPool

try:
    from Queue import Empty, Full, Queue, LifoQueue
except ImportError:
    from queue import Empty, Full, Queue, LifoQueue


LOGGER = logging.getLogger(__name__)
QUEUE_MAX_SIZE = 50


class ThreadBase(object):
    """
    Thread interface
    """
    def __init__(self, exit_event, input_queue=None, output_queue=None, name=None, loop_impl=None):
        super(ThreadBase, self).__init__()
        self.input_queue = input_queue
        self.output_queue = output_queue
        self.exit_event = exit_event
        self.loop_impl_callable = loop_impl
        self.stop_asked = False
        self.name = name or self.__class__.__name__
        self.processing_item = False

    def can_stop(self):
        if self.processing_item:
            return False
        if self.input_queue is not None:
            return self.input_queue.empty()
        return True

    def stop(self):
        self.stop_asked = True

    def loop_impl(self):
        if self.loop_impl_callable is None:
            raise NotImplementedError()
        self.loop_impl_callable()

    def pop_input(self):
        try:
            msg = self.input_queue.get(block=True, timeout=1)
            self.processing_item = True
            return msg
        except Empty:
            self.processing_item = False
            return None

    def put_to_output(self, msg):
        self.output_queue.put(msg)
        self.task_done()

    def task_done(self):
        if self.input_queue is not None:
            self.input_queue.task_done()
        self.processing_item = False

    def init(self):
        pass

    def close(self):
        pass

    def _run(self):
        while not self.stop_asked:
            self.loop_impl()

    def run(self):
        try:
            self.init()
            self._run()
        except Exception:
            LOGGER.error(traceback.format_exc())
            self.exit_event.set()
        finally:
            try:
                self.close()
            except Exception:
                LOGGER.error(traceback.format_exc())
                self.exit_event.set()
        LOGGER.info('Quitting {}'.format(self.name))


class Thread(ThreadBase):
    def __init__(self, *args, **kwargs):
        super(Thread, self).__init__(*args, **kwargs)
        self.thread = ThreadPool(1)

    def start(self):
        self.thread.spawn(self.run)

    def join(self):
        self.thread.join()


class Greenlet(ThreadBase):
    def __init__(self, *args, **kwargs):
        super(Greenlet, self).__init__(*args, **kwargs)
        self.greenlet = None

    def start(self):
        self.greenlet = gevent.spawn(self.run)

    def join(self):
        if self.greenlet is not None:
            self.greenlet.join()

    def put_to_output(self, msg):
        while True:
            try:
                self.output_queue.put(msg, block=True, timeout=0.0001)
                self.task_done()
                break
            except Full:
                # important: yield the execution to other greenlets
                gevent.sleep(0)

    def pop_input(self):
        try:
            msg = self.input_queue.get(block=True, timeout=0.0001)
            self.processing_item = True
            return msg
        except Empty:
            self.processing_item = False
            # important: yield the execution to other greenlets
            gevent.sleep(0)
            return None


class Pool(object):
    def __init__(self, nb_thread, thread_cls=Thread, thread_args=(), thread_kwargs=None, name=None):
        self.nb_thread = nb_thread
        self.name = name or thread_cls.__name__
        self.threads = []
        self.thread_cls = thread_cls
        self.thread_args = thread_args
        self.thread_kwargs = thread_kwargs or {}

    def start(self):
        for i in range(self.nb_thread):
            th = self.thread_cls(*self.thread_args, **self.thread_kwargs)
            th.name = '{}_{}'.format(self.name, i)
            self.threads.append(th)
            th.start()

    def can_stop(self):
        for th in self.threads:
            if not th.can_stop():
                return False
        return True

    def stop(self):
        for th in self.threads:
            th.stop()

    def join(self):
        for th in self.threads:
            th.join()


def clear_queues(queues):
    # Makes sure all queues are empty
    LOGGER.info("Purging queues")
    while True:
        for queue in queues:
            with queue.mutex:
                queue.queue.clear()
        gevent.sleep(0.01)
        if all([queue.empty() for queue in queues]):
            break
    LOGGER.info("Purging queues done")


def stop_when_pools_empty(pools):
    while True:
        can_stop = True
        for pool in pools:
            if not pool.can_stop():
                can_stop = False
                break
        if can_stop:
            break
        gevent.sleep(0.3)

    for pool in pools:
        pool.stop()


@contextmanager
def disable_keyboard_interrupt():
    s = signal.signal(signal.SIGINT, signal.SIG_IGN)
    try:
        yield
    finally:
        signal.signal(signal.SIGINT, s)


def run_pools(pools, queues, pbar, cleanup=None, join_first_pool=True):
    stop_asked = 0
    # Start threads
    for pool in pools:
        pool.start()

    while True:
        try:
            # The first pool is usually the pool that get data from somewhere and push them to the rest of the pipeline
            # So we want to make sure everything has been pushed first before considering the pipeline over
            # But in feedback command this is the main thread that do this so it is done before any pool is started
            if join_first_pool:
                pools[0].join()

            stop_when_pools_empty(pools)

            break
        except (KeyboardInterrupt, SystemExit):
            with disable_keyboard_interrupt():
                stop_asked += 1
                if stop_asked >= 2:
                    LOGGER.info("Hard stop")
                    for pool in pools:
                        pool.stop()

                    # clearing queues to make sure a thread
                    # is not blocked in a queue.put() because of maxsize
                    clear_queues(queues)
                    break
                else:
                    LOGGER.info('Stop asked, waiting for threads to process queued messages.')
                    # stopping inputs
                    pools[0].stop()

    with disable_keyboard_interrupt():
        # Makes sure threads finish properly so that
        # we can make sure the workflow is not used and can be closed
        for pool in pools:
            pool.join()

        pbar.close()
        if cleanup is not None:
            cleanup()
    return stop_asked
