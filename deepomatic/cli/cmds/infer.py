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
        self._worker_queue = worker_queue
        self._output_queue = output_queue
        self._workflow = workflow
        self._workflow_lock = workflow_lock
        self._args = kwargs
        self._threshold = kwargs.get('threshold', None)

    def run(self):
        try:
            while True:
                data = self._worker_queue.get()
                if data == TERMINATION_MSG:
                    self._worker_queue.task_done()
                    self._output_queue.put(TERMINATION_MSG)
                    self._workflow.close()
                    return
                elif data == END_OF_STREAM_MSG:
                    self._worker_queue.task_done()
                    if not self._worker_queue.empty():
                        self._worker_queue.put(END_OF_STREAM_MSG)
                        continue
                    else:
                        self._output_queue.put(END_OF_STREAM_MSG)
                        self._workflow.close()
                        return
                else:
                    frame_processed = None
                    frame_number, name, filename, frame, inference = data
                    if inference is not None:
                        with self._workflow_lock:
                            prediction = inference.get_predictions()
                            # If the prediction is not finished, then put the data back in the queue
                            if prediction is None:
                                self._worker_queue.task_done()
                                self._worker_queue.put(data)
                                continue

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
                        frame_processed = self.processing(name, frame, prediction)

                    self._worker_queue.task_done()
                    self._output_queue.put((frame_number, frame_processed))
        except KeyboardInterrupt:
            logging.info('Stopping output')
            while not self._output_queue.empty():
                try:
                    self._output_queue.get(False)
                except Empty:
                    break
                self._output_queue.task_done()
            self._output_queue.put(TERMINATION_MSG)
            self._workflow.close()

    def processing(self, name, frame, prediction):
        return name, None, prediction


def main(args, force=False):
    try:
        io_data.input_loop(args, InferenceThread)
    except KeyboardInterrupt:
        pass
