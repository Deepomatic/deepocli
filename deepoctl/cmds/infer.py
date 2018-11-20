import os
import sys
import json
import threading
import logging
import datetime
import progressbar

import deepoctl.io_data as io_data
import deepoctl.workflow_abstraction as wa

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

    def processing(self, name, frame, prediction):
        return name, None, prediction

def main(args, force=False):
    io_data.input_loop(args, InferenceThread)
    try:
        io_data.input_loop(args, InferenceThread)
    except KeyboardInterrupt:
        pass
    except:
        logging.error("Unexpected error: %s" % sys.exc_info()[0])