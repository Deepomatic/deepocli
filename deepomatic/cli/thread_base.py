import threading
import time

POP_TIMEOUT = 1


class ThreadBase(threading.Thread):
    def __init__(self, name, input_queue=None):
        super(ThreadBase, self).__init__(name=name)
        self.input_queue = input_queue
        self.stop_asked = False
        self.daemon = True

    def stop_when_no_input(self):
        if self.input_queue is not None:
            while not self.input_queue.empty():
                time.sleep(0.2)
        self.stop()

    def stop(self):
        self.stop_asked = True

    def loop_impl(self):
        raise NotImplementedError()

    def close(self):
        pass

    def run(self):
        while not self.stop_asked:
            self.loop_impl()
        self.close()
