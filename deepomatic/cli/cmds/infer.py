import cv2

try:
    from Queue import Empty
except ImportError:
    from queue import Empty

from .. import thread_base


# Draw parameters
SCORE_DECIMAL_PRECISION = 4             # Prediction score decimal number precision
FONT_SCALE = 0.5                        # Size of the font we draw in the image_output
BOX_COLOR = (255, 0, 0)                 # Bounding box color (BGR)
BACKGROUND_COLOR = (0, 0, 255)          # Text background color (BGR)
TEXT_COLOR = (255, 255, 255)            # Text color (BGR)
TAG_TEXT_CORNER = (10, 10)              # Beginning of text tag column (pixel)
TAG_TEXT_INTERSPACE = 5                 # Vertical space between tags in tag column (pixel)


def substract_tuple(tuple1, tuple2):
    return tuple(x - y for x, y in zip(tuple1, tuple2))


def get_coordinates_from_roi(roi, width, height):
    bbox = roi['bbox']
    xmin = int(bbox['xmin'] * width)
    ymin = int(bbox['ymin'] * height)
    xmax = int(bbox['xmax'] * width)
    ymax = int(bbox['ymax'] * height)
    return (xmin, ymin, xmax, ymax)


class DrawImagePostprocessing(object):

    def __init__(self, **kwargs):
        self._draw_labels = kwargs.get('draw_labels', False)
        self._draw_scores = kwargs.get('draw_scores', False)

    def __call__(self, frame):
        frame.output_image = frame.image.copy()
        output_image = frame.output_image
        height = output_image.shape[0]
        width = output_image.shape[1]
        tag_drawn = 0  # Used to store the number of tags already drawn
        for pred in frame.predictions['outputs'][0]['labels']['predicted']:
            # Build legend
            label = ''
            if self._draw_labels:
                label = pred['label_name']
            if self._draw_labels and self._draw_scores:
                label += ' '
            if self._draw_scores:
                label += str(round(pred['score'], SCORE_DECIMAL_PRECISION))
            # Make sure labels are ascii
            label = str(label.encode('ascii', 'replace'))

            # Get text draw parameters
            ret, baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, FONT_SCALE, 1)

            # If we have a bounding box
            roi = pred.get('roi')
            if roi is not None:
                # Retrieve coordinates
                xmin, ymin, xmax, ymax = get_coordinates_from_roi(roi, width, height)

                # Draw bounding box
                cv2.rectangle(output_image, (xmin, ymin), (xmax, ymax), BOX_COLOR, 1)

                # First get ideal corners
                background_corner1 = (xmin, ymax + 2)
                background_corner2 = (background_corner1[0] + ret[0], background_corner1[1] + ret[1] + baseline)
                text_corner = (background_corner1[0], background_corner1[1] + ret[1])

                # Then make sure they fit in the image
                # For x-axis, simply shift the box to the left
                # For y-axis, put the label at the top if it doesn't fit under the box
                x_offset = max(0, background_corner2[0] - width + 1)
                if background_corner2[1] > height - 1:
                    y_offset = background_corner2[1] - ymin + 2
                else:
                    y_offset = 0
                background_corner1 = substract_tuple(background_corner1, (x_offset, y_offset))
                background_corner2 = substract_tuple(background_corner2, (x_offset, y_offset))
                text_corner = substract_tuple(text_corner, (x_offset, y_offset))

                # Finally draw everything
                cv2.rectangle(output_image, background_corner1, background_corner2, BACKGROUND_COLOR, -1)
                cv2.putText(output_image, label, text_corner, cv2.FONT_HERSHEY_SIMPLEX, FONT_SCALE, TEXT_COLOR, 1)
            elif label != '':
                # First get ideal corners
                if tag_drawn == 0:
                    background_corner1 = TAG_TEXT_CORNER
                else:
                    background_corner1 = (TAG_TEXT_CORNER[0], background_corner2[1] + TAG_TEXT_INTERSPACE)
                background_corner2 = (background_corner1[0] + ret[0], background_corner1[1] + ret[1] + baseline)
                text_corner = (background_corner1[0], background_corner1[1] + ret[1])

                # Finally draw everything
                cv2.rectangle(output_image, background_corner1, background_corner2, BACKGROUND_COLOR, -1)
                cv2.putText(output_image, label, text_corner, cv2.FONT_HERSHEY_SIMPLEX, FONT_SCALE, TEXT_COLOR, 1)
                tag_drawn += 1


class BlurImagePostprocessing(object):
    def __init__(self, **kwargs):
        self._method = kwargs.get('blur_method', 'pixel')
        self._strength = int(kwargs.get('blur_strength', 10))

    def __call__(self, frame):
        frame.output_image = frame.image.copy()
        output_image = frame.output_image
        height = output_image.shape[0]
        width = output_image.shape[1]
        for pred in frame.predictions['outputs'][0]['labels']['predicted']:
            # Check that we have a bounding box
            roi = pred.get('roi')
            if roi is not None:
                # Retrieve coordinates
                xmin, ymin, xmax, ymax = get_coordinates_from_roi(roi, width, height)

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
        self.frames_to_check_first = []

    def close(self):
        self.frames_to_check_first = []

    def can_stop(self):
        return super(ResultInferenceThread, self).can_stop() and \
            len(self.frames_to_check_first) == 0

    def fill_predictions(self, predictions, new_predicted, new_discarded):
        for prediction in predictions:
            if prediction['score'] >= self.threshold:
                new_predicted.append(prediction)
            else:
                new_discarded.append(prediction)

    def loop_impl(self):
        # we keep an internal cache that we re-check when it is big or that the input_queue is empty
        if len(self.frames_to_check_first) > 10:
            frame = self.frames_to_check_first.pop(0)
        else:
            try:
                frame = self.input_queue.get(timeout=thread_base.POP_TIMEOUT)
                self.input_queue.task_done()
            except Empty:
                if not self.frames_to_check_first:
                    return
                frame = self.frames_to_check_first.pop(0)

        predictions = frame.inference_async_result.get_predictions()

        # If the prediction is not finished, then put the data back in the queue
        if predictions is None:
            self.frames_to_check_first.append(frame)
            return

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
