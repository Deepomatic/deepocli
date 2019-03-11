import os
import sys
import json
import copy
import threading
import logging

try:
    from Queue import Empty
except ImportError:
    from queue import Empty

from deepomatic.cli.cmds.studio_helpers.vulcan2studio import transform_json_from_vulcan_to_studio
from deepomatic.cli import io_data
from deepomatic.cli.workflow import get_workflow

class InferenceThread(threading.Thread):
    def __init__(self, input_queue, output_queue, **kwargs):
        threading.Thread.__init__(self, args=(), kwargs=None)
        self.input_queue = input_queue
        self.output_queue = output_queue
        self.daemon = True
        self.workflow = get_workflow(kwargs)
        self.args = kwargs
        self._threshold = kwargs.get('threshold', None)

    def run(self):
        try:
            while True:
                data = self.input_queue.get()

                if data is None:
                    self.input_queue.task_done()
                    self.output_queue.put(None)
                    self.workflow.close()
                    return

                result = None
                name, filename, frame = data
                if frame is not None:
                    if self.workflow is not None:
                        # Computes prediction and formats them to studio json format
                        prediction = self.workflow.infer(frame).get()
                        prediction = transform_json_from_vulcan_to_studio(prediction, name, filename)

                        # Keep only predictions higher than threshold if one is set, otherwise use the model thresholds
                        kept_pred = []
                        for pred in prediction['images'][0]['annotated_regions']:
                            if self._threshold:
                                if pred['score'] >= self._threshold:
                                    kept_pred.append(pred)
                            else:
                                if pred['score'] >= pred['threshold']:
                                    kept_pred.append(pred)
                        prediction['images'][0]['annotated_regions'] = copy.deepcopy(kept_pred)
                    else:
                        prediction = {'tags': [], 'images': []}

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
            self.workflow.close()

    def processing(self, name, frame, prediction):
        return name, None, prediction


def main(args, force=False):
    try:
        io_data.input_loop(args, InferenceThread)
    except KeyboardInterrupt:
        pass
