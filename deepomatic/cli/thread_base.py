import logging
import traceback
import heapq
import gevent
import signal
from contextlib import contextmanager
from gevent.threadpool import ThreadPool
from threading import Lock
from .common import clear_queue, Full, Empty


LOGGER = logging.getLogger(__name__)
QUEUE_MAX_SIZE = 50
SLEEP_TIME = 0.0001  # don't touch until we have non performance regression tests


@contextmanager
def try_lock(lock):
    acquired = lock.acquire(False)
    try:
        yield acquired
    finally:
        if acquired:
            lock.release()


@contextmanager
def blocking_lock(lock, sleep_time=SLEEP_TIME):
    while True:
        # avoid lock totally the main thread and blocking greenlets
        # it may take a little more time to lock if it is not lucky
        # though you can decrease sleep_time to have more luck
        gevent.sleep(sleep_time)
        with try_lock(lock) as acquired:
            if acquired:
                yield
                return


class CurrentMessages(object):
    """
    Track all messages currently being processed in the Pipeline
    """
    def __init__(self):
        self.heap_lock = Lock()
        self.messages = []

    def lock(self):
        return blocking_lock(self.heap_lock)

    def add_message(self, msg):
        with self.lock():
            heapq.heappush(self.messages, msg)

    def get_min(self):
        with self.lock():
            if len(self.messages) > 0:
                return heapq.nsmallest(1, self.messages)[0]
        return None

    def pop_min(self):
        with self.lock():
            if len(self.messages) > 0:
                return heapq.heappop(self.messages)
        return None

    def forget_message(self, msg):
        try:
            with self.lock():
                self.messages.remove(msg)
                heapq.heapify(self.messages)
        except ValueError as e:
            LOGGER.error(e)


class ThreadBase(object):
    """
    Thread interface
    """
    def __init__(self, exit_event, input_queue=None, output_queue=None, current_messages=None, name=None):
        super(ThreadBase, self).__init__()
        self.input_queue = input_queue
        self.output_queue = output_queue
        self.exit_event = exit_event
        self.stop_asked = False
        self.name = name or self.__class__.__name__
        self.processing_item_lock = Lock()
        self.current_messages = current_messages
        self.alive = False

    def try_lock(self):
        return try_lock(self.processing_item_lock)

    def can_stop(self):
        if self.input_queue is not None:
            if not self.input_queue.empty():
                return False
        return True

    def stop(self):
        self.stop_asked = True

    def stop_when_empty(self):
        long_sleep = 0.05
        sleep_time = long_sleep
        while True:
            # don't touch until we have non performance regression tests
            gevent.sleep(sleep_time)
            # try to acquire only sometimes
            with self.try_lock() as acquired:
                if acquired:
                    sleep_time = long_sleep
                    if self.can_stop():
                        self.stop()
                        return
                else:
                    sleep_time = SLEEP_TIME
            if not self.alive:
                return

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
                # don't touch until we have non performance regression tests
                gevent.sleep(SLEEP_TIME)

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
            with self.try_lock() as acquired:
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
            if empty:
                # don't touch until we have non performance regression tests
                gevent.sleep(SLEEP_TIME)

    def run(self):
        self.alive = True
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
        self.alive = False


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


class MainLoop(object):
    def __init__(self, pools, queues, pbar, cleanup_func=None):
        self.pools = pools
        self.queues = queues
        self.pbar = pbar
        self.cleanup_func = cleanup_func
        self.stop_asked = 0

    def clear_queues(self):
        # Makes sure all queues are empty
        LOGGER.info("Purging queues")
        while True:
            for queue in self.queues:
                clear_queue(queue)
            if all([queue.empty() for queue in self.queues]):
                break
        LOGGER.info("Purging queues done")

    @contextmanager
    def disable_exit_signals(self):
        gevent.signal(signal.SIGINT, lambda: signal.SIG_IGN)
        gevent.signal(signal.SIGTERM, lambda: signal.SIG_IGN)
        try:
            yield
        finally:
            gevent.signal(signal.SIGINT, self.stop)
            gevent.signal(signal.SIGTERM, self.stop)

    def stop(self):
        with self.disable_exit_signals():
            self.stop_asked += 1
            if self.stop_asked < 2:
                LOGGER.info('Stop asked, waiting for threads to process queued messages.')
                # stopping inputs
                self.pools[0].stop()
            elif self.stop_asked == 2:
                LOGGER.info("Hard stop")
                for pool in self.pools:
                    pool.stop()

                # clearing queues to make sure a thread
                # is not blocked in a queue.put() because of maxsize
                self.clear_queues()

    def run_forever(self):

        # Start threads
        for pool in self.pools:
            pool.start()

        gevent.signal(gevent.signal.SIGINT, self.stop)
        gevent.signal(gevent.signal.SIGTERM, self.stop)

        for pool in self.pools:
            pool.stop_when_empty()

        gevent.signal(gevent.signal.SIGINT, lambda: signal.SIG_IGN)
        gevent.signal(gevent.signal.SIGTERM, lambda: signal.SIG_IGN)
        # Makes sure threads finish properly so that
        # we can make sure the workflow is not used and can be closed
        for pool in self.pools:
            pool.join()

        self.pbar.close()
        if self.cleanup_func is not None:
            self.cleanup_func()
        return self.stop_asked
