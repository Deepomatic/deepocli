import cv2
import os
import time

try:
    from Queue import Empty
except ImportError:
    from queue import Empty

from .. import thread_base


# Size of the font we draw in the image_output
FONT_SCALE = 0.5
RESULT_BATCH_SIZE = int(os.getenv('RESULT_BATCH_SIZE', 10))


class DrawImagePostprocessing(object):

    def __init__(self, **kwargs):
        self._draw_labels = kwargs.get('draw_labels', False)
        self._draw_scores = kwargs.get('draw_scores', False)

    def __call__(self, frame):
        frame.output_image = frame.image.copy()
        output_image = frame.output_image
        h = output_image.shape[0]
        w = output_image.shape[1]
        for pred in frame.predictions['outputs'][0]['labels']['predicted']:
            # Check that we have a bounding box
            roi = pred.get('roi')
            if roi is not None:
                # Build legend
                label = ''
                if self._draw_labels:
                    label += ', ' + pred['label_name']
                if self._draw_labels and self._draw_scores:
                    label += ' '
                if self._draw_scores:
                    label += str(pred['score'])

                # Retrieve coordinates
                bbox = roi['bbox']
                xmin = int(bbox['xmin'] * w)
                ymin = int(bbox['ymin'] * h)
                xmax = int(bbox['xmax'] * w)
                ymax = int(bbox['ymax'] * h)

                # Draw bounding box
                color = (255, 0, 0)
                cv2.rectangle(output_image, (xmin, ymin), (xmax, ymax), color, 1)
                ret, baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, FONT_SCALE, 1)
                cv2.rectangle(output_image, (xmin, ymax - ret[1] - baseline), (xmin + ret[0], ymax), (0, 0, 255), -1)
                cv2.putText(output_image, label, (xmin, ymax - baseline), cv2.FONT_HERSHEY_SIMPLEX, FONT_SCALE, (255, 255, 255), 1)


class BlurImagePostprocessing(object):
    def __init__(self, **kwargs):
        self._method = kwargs.get('blur_method', 'pixel')
        self._strength = int(kwargs.get('blur_strength', 10))

    def __call__(self, frame):
        frame.output_image = frame.image.copy()
        output_image = frame.output_image
        h = output_image.shape[0]
        w = output_image.shape[1]
        for pred in frame.predictions['outputs'][0]['labels']['predicted']:
            # Check that we have a bounding box
            roi = pred.get('roi')
            if roi is not None:
                # Retrieve coordinates
                bbox = roi['bbox']
                xmin = int(bbox['xmin'] * w)
                ymin = int(bbox['ymin'] * h)
                xmax = int(bbox['xmax'] * w)
                ymax = int(bbox['ymax'] * h)

                # Draw
                if self._method == 'black':
                    cv2.rectangle(output_image, (xmin, ymin), (xmax, ymax), (0, 0, 0), -1)
                elif self._method == 'gaussian':
                    rectangle = frame[ymin:ymax, xmin:xmax]
                    rectangle = cv2.GaussianBlur(rectangle, (15, 15), self._strength)
                    output_image[ymin:ymax, xmin:xmax] = rectangle
                elif self._method == 'pixel':
                    rectangle = output_image[ymin:ymax, xmin:xmax]
                    small = cv2.resize(rectangle, (0, 0),
                                       fx=1. / min((xmax - xmin), self._strength),
                                       fy=1. / min((ymax - ymin), self._strength))
                    rectangle = cv2.resize(small, ((xmax - xmin), (ymax - ymin)),
                                           interpolation=cv2.INTER_NEAREST)
                    output_image[ymin:ymax, xmin:xmax] = rectangle


class SendInferenceThread(thread_base.ThreadBase):
    def __init__(self, exit_event, input_queue, output_queue, workflow, **kwargs):
        super(SendInferenceThread, self).__init__(exit_event, 'SendInferenceThread', input_queue)
        self.output_queue = output_queue
        self.workflow = workflow
        self.args = kwargs

    def loop_impl(self):
        try:
            frame = self.input_queue.get(timeout=thread_base.POP_TIMEOUT)
        except Empty:
            return

        _, buf = cv2.imencode('.jpeg', frame.image)
        buf_bytes = buf.tobytes()
        frame.inference_async_result = self.workflow.infer(buf_bytes)

        self.input_queue.task_done()
        self.output_queue.put(frame)


class ResultInferenceThread(thread_base.ThreadBase):
    def __init__(self, exit_event, input_queue, output_queue, workflow, **kwargs):
        super(ResultInferenceThread, self).__init__(exit_event, 'ResultInferenceThread', input_queue)
        self.output_queue = output_queue
        self.workflow = workflow
        self.args = kwargs
        self.postprocessing = kwargs.get('postprocessing')
        self.threshold = kwargs.get('threshold')
        self.batch = []

    def close(self):
        self.batch = []

    def can_stop(self):
        return super(ResultInferenceThread, self).can_stop() and \
            len(self.batch) == 0

    def fill_predictions(self, predictions, new_predicted, new_discarded):
        for prediction in predictions:
            if prediction['score'] >= self.threshold:
                new_predicted.append(prediction)
            else:
                new_discarded.append(prediction)

    def _run(self):
        sleep_time = 0.
        sleep_time_inc = 0.005
        while not self.stop_asked:
            # We try to get a whole batch
            for i in range(RESULT_BATCH_SIZE):
                try:
                    frame = self.input_queue.get(timeout=thread_base.POP_TIMEOUT)
                    self.batch.append(frame)
                except Empty:
                    break

            time.sleep(sleep_time)
            not_done = 0
            # We wait for the whole batch
            while self.batch:
                frame = self.batch.pop(0)

                predictions = frame.inference_async_result.get_predictions()

                # If the prediction is not finished, then put the data back in the batch
                # and increase the sleep time so that we use less cpu for the next batch
                if predictions is None:
                    self.batch.append(frame)
                    sleep_time += sleep_time_inc
                    not_done += 1
                    continue

                if self.threshold is not None:
                    # Keep only predictions higher than threshold
                    for output in predictions['outputs']:
                        new_predicted = []
                        new_discarded = []
                        labels = output['labels']
                        self.fill_predictions(labels['predicted'], new_predicted, new_discarded)
                        self.fill_predictions(labels['discarded'], new_predicted, new_discarded)
                        labels['predicted'] = new_predicted
                        labels['discarded'] = new_discarded

                frame.predictions = predictions

                if self.postprocessing is not None:
                    self.postprocessing(frame)
                else:
                    frame.output_image = frame.image  # we output the original image

                self.output_queue.put(frame)

            if not_done == 0:
                # we adjust the sleep time depending on the speed of the worker(s)
                # here everything was done in one iteration over the batch
                # so we consider we can sleep less for the next batch
                sleep_time = max(sleep_time - sleep_time_inc, 0.)
