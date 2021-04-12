from .thread_base import CurrentMessages


class Frame(object):
    def __init__(self, name, filename, image, decoded_video_frame_index=None, absolute_video_frame_index=None):
        # The Frame object is used as a data exchanged in the different queues
        self.name = name  # name of the frame
        self.filename = filename  # the original filename from which the frame was extracted
        self.image = image  # an opencv loaded image (numpy array)
        self.decoded_video_frame_index = decoded_video_frame_index  # frame index in the input sequence (skipped frames are not included)
        self.absolute_video_frame_index = absolute_video_frame_index  # frame index in the input sequence (skipped frames included)
        self.frame_number = None  # frame_number since deepocli started (set by input_loop)
        self.inference_async_result = None  # an inference request object that will allow us to retrieve the predictions when ready
        self.predictions = None  # predictions result dict
        self.output_image = None  # frame to output (modified version of the image, check infer postprocessings draw/blur)
        self.buf_bytes = None

    def __str__(self):
        return "<Frame {}>".format(' '.join("{}={}".format(key, getattr(self, key)) for key in [
            'name',
            'filename',
            'frame_number',
            'decoded_video_frame_index',
            'absolute_video_frame_index',
            'inference_async_result']))


class CurrentFrames(CurrentMessages):
    def forget_frame(self, frame, count_as_error=True):
        self.forget_message(frame.frame_number, count_as_error=count_as_error)

    def add_frame(self, frame):
        self.add_message(frame.frame_number)

    def get_oldest(self):
        return self.get_min()

    def pop_oldest(self):
        return self.pop_min()
