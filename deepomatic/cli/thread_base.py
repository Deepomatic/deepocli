import logging
import traceback
import heapq
import gevent
import signal
from contextlib import contextmanager
from gevent.threadpool import ThreadPool
from threading import Lock
from .common import clear_queue, Full, Empty
from deepomatic.api.exceptions import BadStatus
from .exceptions import DeepoCLIException


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
    Track all messages currently being processed in the Pipeline.
    Also allow to track number of errors.
    """
    def __init__(self):
        self.heap_lock = Lock()
        self.messages = []
        self.nb_errors = 0
        self.nb_successes = 0
        self.nb_added_messages = 0

    def lock(self):
        return blocking_lock(self.heap_lock)

    def add_message(self, msg):
        with self.lock():
            heapq.heappush(self.messages, msg)
            self.nb_added_messages += 1

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

    def report_success(self):
        self.report_successes(1)

    def report_successes(self, nb_successes):
        with self.lock():
            self.nb_successes += nb_successes

    def report_error(self):
        self.report_errors(1)

    def report_errors(self, nb_errors):
        with self.lock():
            self.nb_errors += nb_errors

    def report_message(self):
        self.report_messages(1)

    def report_messages(self, nb_messages):
        with self.lock():
            self.nb_added_messages += nb_messages

    def forget_message(self, msg, count_as_error=True):
        try:
            with self.lock():
                if count_as_error:
                    self.nb_errors += 1
                self.messages.remove(msg)
                heapq.heapify(self.messages)
        except ValueError as e:
            # TODO: remove the try/catch
            # we should call it only if we are sure the message it there
            LOGGER.error(str(e))


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
        # Allow to not stop when an item is still being processed
        self.processing_item_lock = Lock()
        self.current_messages = current_messages
        self.alive = False

    def try_lock(self):
        return try_lock(self.processing_item_lock)

    def can_stop(self):
        if self.input_queue is not None and not self.input_queue.empty():
            return False
        return True

    def stop(self):
        # Can be called from the same thread or from another
        self.stop_asked = True

    def wait_until_nothing_to_process(self):
        # Must be called externally (from another thread)

        if self.input_queue is None:
            # When ThreadBase has no input queue
            # Either the ThreadBase stop by itself by calling self.stop()
            # Either another thread call thread/pool.stop()
            # Otherwise it will wait indefinitely
            self.join()
            return

        # When ThreadBase has an input queue and previous pools are stopped
        # We can stop when the input queue is empty
        long_sleep = 0.05
        sleep_time = long_sleep
        while not self.exit_event.is_set():
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
                break
            except Full:
                # don't touch until we have non performance regression tests
                gevent.sleep(SLEEP_TIME)

    def task_done(self, msg_in, msg_out):
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
                        self.task_done(msg_in, msg_out)
            if empty:
                # don't touch until we have non performance regression tests
                gevent.sleep(SLEEP_TIME)

    def run(self):
        self.alive = True
        try:
            self.init()
            self._run()
        except DeepoCLIException as e:
            LOGGER.error(e)
            self.exit_event.set()
        except BadStatus as e:
            if e.status_code >= 400 and e.status_code < 500:
                LOGGER.error("API raised a bad status code {}: {}".format(
                    e.status_code, e.content
                ))
            else:
                # TODO: we probably want to retry on some errors earlier in the greenlet
                LOGGER.error("Encountered an unexpected exception during routine: {}".format(traceback.format_exc()))
            self.exit_event.set()
        except Exception:
            LOGGER.error("Encountered an unexpected exception during routine: {}".format(traceback.format_exc()))
            self.exit_event.set()
        finally:
            try:
                self.close()
            except Exception:
                LOGGER.error("Encountered an unexpected exception during routine closing: {}".format(traceback.format_exc()))
                self.exit_event.set()
        LOGGER.debug('Quitting {}'.format(self.name))
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
        thread_kwargs = thread_kwargs or {}
        for i in range(self.nb_thread):
            th = thread_cls(*thread_args, **thread_kwargs)
            th.name = '{}_{}'.format(self.name, i)
            self.threads.append(th)

    def start(self):
        for th in self.threads:
            th.start()

    def wait_until_nothing_to_process(self):
        # Must be called externally (from another thread)
        for th in self.threads:
            th.wait_until_nothing_to_process()

    def stop(self):
        for th in self.threads:
            th.stop()

    def join(self):
        for th in self.threads:
            th.join()


class MainLoop(object):
    def __init__(self, pools, queues, pbar, exit_event,
                 current_messages, cleanup_func=None):
        self.pools = pools
        self.queues = queues
        self.pbar = pbar
        self.exit_event = exit_event
        self.current_messages = current_messages
        self.cleanup_func = cleanup_func
        self.stop_asked = 0
        self.cleaned = False

    def clear_queues(self):
        # Makes sure all queues are empty
        LOGGER.debug("Purging queues")
        while True:
            for queue in self.queues:
                clear_queue(queue)
            if all([queue.empty() for queue in self.queues]):
                break
        LOGGER.debug("Purging queues done")

    @contextmanager
    def disable_exit_signals(self):
        gevent.signal_handler(signal.SIGINT, lambda: signal.SIG_IGN)
        gevent.signal_handler(signal.SIGTERM, lambda: signal.SIG_IGN)
        try:
            yield
        finally:
            gevent.signal_handler(signal.SIGINT, self.stop)
            gevent.signal_handler(signal.SIGTERM, self.stop)

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

    def cleanup(self):
        if self.cleaned:
            return
        if self.cleanup_func is not None:
            self.cleanup_func()

        # Compute the stats on number of errors
        # pbar total may be None for infinite streams
        total_inputs = float('inf') if self.pbar.total is None else self.pbar.total

        nb_uncompleted = (self.current_messages.nb_added_messages
                          - self.current_messages.nb_errors
                          - self.current_messages.nb_successes)
        self.pbar.close()
        LOGGER.info('Summary: errors={} uncompleted={} successful={} total={}.'.format(self.current_messages.nb_errors,
                                                                                       nb_uncompleted,
                                                                                       self.current_messages.nb_successes,
                                                                                       total_inputs))
        self.cleaned = True

    def run_forever(self):
        # Start threads
        for pool in self.pools:
            pool.start()

        gevent.signal_handler(gevent.signal.SIGINT, self.stop)
        gevent.signal_handler(gevent.signal.SIGTERM, self.stop)

        for pool in self.pools:
            # Either pools stop by themself
            # Or they will get stopped when input queue is empty
            pool.wait_until_nothing_to_process()

        if not self.exit_event.is_set():
            gevent.signal_handler(gevent.signal.SIGINT, lambda: signal.SIG_IGN)
            gevent.signal_handler(gevent.signal.SIGTERM, lambda: signal.SIG_IGN)
            # Makes sure threads finish properly so that
            # we can make sure the workflow is not used and can be closed
            for pool in self.pools:
                pool.join()

        self.cleanup()
        return self.stop_asked
