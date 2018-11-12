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
    def __init__(self, queue, args=(), kwargs=None):
        threading.Thread.__init__(self, args=(), kwargs=None)
        self.queue = queue
        self.daemon = True
        self.workflow = wa.get_workflow(args)
        self.args = args
    
    def run(self):
        with io_data.get_output(self.args.output) as output:
            while True:
                frame = self.queue.get()
                if frame is None:
                    return

                if (self.workflow is not None):
                    detection = self.workflow.infer(frame).get()
                    detection = detection['outputs'][0]['labels']['predicted']
                else:
                    detection = []
                
                result = self.processing(frame, detection)
                self.queue.task_done()
                if output(result):
                    return

    def processing(self, frame, detection):
        return frame

def main(args, force=False):
    try:
        io_data.input_loop(args, InferenceThread)
    except KeyboardInterrupt:
        pass
    except:
        logging.error("Unexpected error: %s" % sys.exc_info()[0])