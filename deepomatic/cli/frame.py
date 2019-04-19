from .thread_base import CurrentMessages


class Frame(object):
    def __init__(self, name, filename, image, video_frame_index=None):
        # The Frame object is used as a data exchanged in the different queues
        self.name = name  # name of the frame
        self.filename = filename  # the original filename from which the frame was extracted
        self.image = image  # an opencv loaded image (numpy array)
        self.video_frame_index = video_frame_index  # index of the frame in the video sequence
        self.frame_number = None  # frame_number since deepocli started (set by input_loop)
        self.inference_async_result = None  # an inference request object that will allow us to retrieve the predictions when ready
        self.predictions = None  # predictions result dict
        self.output_image = None  # frame to output (modified version of the image, check infer postprocessings draw/blur)
        self.buf_bytes = None

    def __str__(self):
        return '<Frame name={} filename={} frame_number={} video_frame_index={}>'.format(
            self.name, self.filename, self.frame_number, self.video_frame_index)


class CurrentFrames(CurrentMessages):
    def forget_frame(self, frame):
        self.forget_message(frame.frame_number)

    def add_frame(self, frame):
        self.add_message(frame.frame_number)

    def get_oldest(self):
        return self.get_min()

    def pop_oldest(self):
        return self.pop_min()
