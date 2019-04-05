import threading
import time
import logging
import traceback

POP_TIMEOUT = 1


class ThreadBase(threading.Thread):
    def __init__(self, exit_event, name, input_queue=None):
        super(ThreadBase, self).__init__(name=name)
        self.input_queue = input_queue
        self.exit_event = exit_event
        self.stop_asked = False
        self.daemon = True

    def can_stop(self):
        if self.input_queue is not None:
            return self.input_queue.empty()
        return True

    def stop_when_no_input(self):
        while not self.can_stop():
            time.sleep(0.2)
        self.stop()

    def stop(self):
        self.stop_asked = True

    def loop_impl(self):
        raise NotImplementedError()

    def init(self):
        pass

    def close(self):
        pass

    def run(self):
        try:
            self.init()
            while not self.stop_asked:
                self.loop_impl()
        except Exception:
            logging.error(traceback.format_exc())
            self.exit_event.set()
        finally:
            try:
                self.close()
            except Exception:
                logging.error(traceback.format_exc())
                self.exit_event.set()
