from deepocli.cmds import infer
from deepocli import io_data


class BlurThread(infer.InferenceThread):
    def __init__(self, input_queue, output_queue, **kwargs):
        super(BlurThread, self).__init__(input_queue, output_queue, **kwargs)
        self.process = io_data.BlurOutputData(**kwargs)

    def processing(self, name, frame, prediction):
        return self.process(name, frame, prediction)


def main(args, force=False):
    try:
        io_data.input_loop(args, BlurThread)
    except KeyboardInterrupt:
        pass
