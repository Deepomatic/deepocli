import os
import sys
import json
import threading
import logging
import datetime
try:
    from Queue import Empty
except ImportError:
    from queue import Empty

import deepomatic.cli.io_data as io_data
import deepomatic.cli.workflow_abstraction as wa

class InferenceThread(threading.Thread):
    def __init__(self, input_queue, output_queue, **kwargs):
        threading.Thread.__init__(self, args=(), kwargs=None)
        self.input_queue = input_queue
        self.output_queue = output_queue
        self.daemon = True
        self.workflow = wa.get_workflow(kwargs)
        self.args = kwargs
        self._threshold = kwargs.get('threshold', 0.7)

    def run(self):
        try:
            while True:
                data = self.input_queue.get()

                if data is None:
                    self.input_queue.task_done()
                    self.output_queue.put(None)
                    return

                name, frame = data
                if self.workflow is not None:
                    prediction = self.workflow.infer(frame).get()
                    prediction = [predicted
                        for predicted in prediction['outputs'][0]['labels']['predicted']
                        if float(predicted['score']) >= float(self._threshold)]
                else:
                    prediction = []

                result = self.processing(name, frame, prediction)
                self.input_queue.task_done()
                self.output_queue.put(result)
        except KeyboardInterrupt:
            logging.info('Stopping output')
            while not self.output_queue.empty():
                try:
                    self.output_queue.get(False)
                except Empty:
                    break
                self.output_queue.task_done()
            self.output_queue.put(None)

    def processing(self, name, frame, prediction):
        return name, None, prediction

def main(args, force=False):
    try:
        io_data.input_loop(args, InferenceThread)
    except KeyboardInterrupt:
        pass