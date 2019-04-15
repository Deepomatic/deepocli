import cv2
import logging

from ..workflow.workflow_abstraction import InferenceError, InferenceTimeout
from .. import thread_base

LOGGER = logging.getLogger(__name__)

# Size of the font we draw in the image_output
FONT_SCALE = 0.5


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


class PrepareInferenceThread(thread_base.Thread):
    def loop_impl(self):
        frame = self.pop_input()
        if frame is None:
            return
        _, buf = cv2.imencode('.jpg', frame.image)
        buf_bytes = buf.tobytes()
        frame.buf_bytes = buf_bytes
        self.put_to_output(frame)


class SendInferenceGreenlet(thread_base.Greenlet):
    def __init__(self, exit_event, input_queue, output_queue, workflow):
        super(SendInferenceGreenlet, self).__init__(exit_event, input_queue, output_queue)
        self.workflow = workflow
        self.push_client = workflow.new_client()

    def close(self):
        self.workflow.close_client(self.push_client)

    def loop_impl(self):
        frame = self.pop_input()
        if frame is None:
            return
        frame.inference_async_result = self.workflow.infer(frame.buf_bytes, self.push_client)
        self.put_to_output(frame)


class ResultInferenceGreenlet(thread_base.Greenlet):
    def __init__(self, exit_event, input_queue, output_queue, workflow, **kwargs):
        super(ResultInferenceGreenlet, self).__init__(exit_event, input_queue, output_queue)
        self.workflow = workflow
        self.threshold = kwargs.get('threshold')

    def fill_predictions(self, predictions, new_predicted, new_discarded):
        for prediction in predictions:
            if prediction['score'] >= self.threshold:
                new_predicted.append(prediction)
            else:
                new_discarded.append(prediction)

    def loop_impl(self):
        frame = self.pop_input()
        if frame is None:
            return
        try:
            predictions = frame.inference_async_result.get_predictions(timeout=60)
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
            self.put_to_output(frame)
        except InferenceError as e:
            LOGGER.error('Error getting predictions for frame {}: {}'.format(frame, str(e)))
        except InferenceTimeout as e:
            LOGGER.error("Couldn't get predictions for the whole batch in enough time ({} seconds). Ignoring frames {}.".format(e.timeout, self.batch))
