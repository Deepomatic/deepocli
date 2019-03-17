import os
import sys
import json
import copy
import logging
import threading

try:
    from Queue import Empty
except ImportError:
    from queue import Empty

from deepomatic.cli import io_data
from deepomatic.cli.io_data import END_OF_STREAM_MSG, TERMINATION_MSG
from deepomatic.cli.cmds.studio_helpers.vulcan2studio import transform_json_from_vulcan_to_studio

class InferenceThread(threading.Thread):
    def __init__(self, worker_queue, output_queue, workflow, workflow_lock, **kwargs):
        threading.Thread.__init__(self, args=(), kwargs=None)
        self.worker_queue = worker_queue
        self.output_queue = output_queue
        self.workflow = workflow
        self.workflow_lock = workflow_lock
        self.args = kwargs
        self.threshold = kwargs.get('threshold', None)

    def run(self):
        try:
            while 1:
                data = self.worker_queue.get()
                if data is TERMINATION_MSG:
                    self.worker_queue.task_done()
                    self.output_queue.put(TERMINATION_MSG)
                    self.workflow.close()
                    return
                elif data is END_OF_STREAM_MSG:
                    self.worker_queue.task_done()
                    if not self.worker_queue.empty():
                        self.worker_queue.put(END_OF_STREAM_MSG)
                        continue
                    else:
                        self.output_queue.put(END_OF_STREAM_MSG)
                        self.workflow.close()
                        return
                else:
                    frame_processed = None
                    frame_number, name, filename, frame, inference = data
                    if inference is not None:
                        with self.workflow_lock:
                            prediction = inference.get_predictions()
                            # If the prediction is not finished, then put the data back in the queue
                            if prediction is None:
                                self.worker_queue.task_done()
                                self.worker_queue.put(data)
                                continue

                        prediction = transform_json_from_vulcan_to_studio(prediction, name, filename)
                        # Keep only predictions higher than threshold if one is set, otherwise use the model thresholds
                        kept_pred = []
                        for pred in prediction['images'][0]['annotated_regions']:
                            if self.threshold:
                                if pred['score'] >= self.threshold:
                                    kept_pred.append(pred)
                            else:
                                if pred['score'] >= pred['threshold']:
                                    kept_pred.append(pred)
                        prediction['images'][0]['annotated_regions'] = copy.deepcopy(kept_pred)
                        frame_processed = self.processing(name, frame, prediction)

                    self.worker_queue.task_done()
                    self.output_queue.put((frame_number, frame_processed))
        except KeyboardInterrupt:
            logging.info('Stopping output')
            while not self.output_queue.empty():
                try:
                    self.output_queue.get(False)
                except Empty:
                    break
                self.output_queue.task_done()
            self.output_queue.put(TERMINATION_MSG)
            self.workflow.close()

    def processing(self, name, frame, prediction):
        return name, None, prediction


def main(args, force=False):
    try:
        io_data.input_loop(args, InferenceThread)
    except KeyboardInterrupt:
        pass
