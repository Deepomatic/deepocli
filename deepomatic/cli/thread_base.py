import logging
import traceback
import gevent
import signal
import time
from contextlib import contextmanager
from gevent.threadpool import ThreadPool
from gevent.lock import Semaphore
from threading import Lock

try:
    from Queue import Empty, Full, Queue, LifoQueue
except ImportError:
    from queue import Empty, Full, Queue, LifoQueue


LOGGER = logging.getLogger(__name__)
QUEUE_MAX_SIZE = 50
SLEEP_TIME = 0.0005


class ThreadBase(object):
    """
    Thread interface
    """
    def __init__(self, exit_event, input_queue=None, output_queue=None, name=None):
        super(ThreadBase, self).__init__()
        self.input_queue = input_queue
        self.output_queue = output_queue
        self.exit_event = exit_event
        self.stop_asked = False
        self.name = name or self.__class__.__name__
        self.processing_item_lock = Lock()

    @contextmanager
    def lock(self):
        acquired = self.processing_item_lock.acquire(False)
        try:
            yield acquired
        finally:
            if acquired:
                self.processing_item_lock.release()

    def can_stop(self):
        if self.input_queue is not None:
            if not self.input_queue.empty():
                return False
        return True

    def stop(self):
        self.stop_asked = True

    def stop_when_empty(self):
        while True:
            with self.lock() as acquired:
                if acquired:
                    if self.can_stop():
                        self.stop()
                        return

            self.sleep(SLEEP_TIME)

    def process_msg(self, msg):
        raise NotImplementedError()

    def pop_input(self):
        return self.input_queue.get(block=False)

    def put_to_output(self, msg_out):
        while True:
            try:
                self.output_queue.put(msg_out, block=False)
                self.task_done()
                break
            except Full:
                self.sleep(SLEEP_TIME)

    def task_done(self):
        if self.input_queue is not None:
            self.input_queue.task_done()

    def init(self):
        pass

    def close(self):
        pass

    def _run(self):
        while not self.stop_asked:
            empty = False
            with self.lock() as acquired:
                if acquired:
                    msg_in = None
                    if self.input_queue is not None:
                        try:
                            msg_in = self.pop_input()
                        except Empty:
                            empty = True
                    if self.input_queue is None or not empty:
                        msg_out = self.process_msg(msg_in)
                        if msg_out is not None:
                            self.put_to_output(msg_out)

            self.sleep(SLEEP_TIME)

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

    def sleep(self, t):
        # time.sleep(t)
        gevent.sleep(t)


class Greenlet(ThreadBase):
    def __init__(self, *args, **kwargs):
        super(Greenlet, self).__init__(*args, **kwargs)
        self.greenlet = None

    def start(self):
        self.greenlet = gevent.spawn(self.run)

    def join(self):
        if self.greenlet is not None:
            self.greenlet.join()

    def sleep(self, t):
        gevent.sleep(t)


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

    def stop_when_empty(self):
        for th in self.threads:
            th.stop_when_empty()

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
        if all([queue.empty() for queue in queues]):
            break
    LOGGER.info("Purging queues done")


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

            for pool in pools:
                pool.stop_when_empty()

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

    print("Joining !")
    with disable_keyboard_interrupt():
        # Makes sure threads finish properly so that
        # we can make sure the workflow is not used and can be closed
        for pool in pools:
            pool.join()

        pbar.close()
        if cleanup is not None:
            cleanup()
    return stop_asked
