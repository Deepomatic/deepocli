from deepomatic.cli.cmds import infer
from deepomatic.cli import io_data


class DrawThread(infer.InferenceThread):
    def __init__(self, input_queue, output_queue, **kwargs):
        super(DrawThread, self).__init__(input_queue, output_queue, **kwargs)
        self.process = io_data.DrawOutputData(**kwargs)

    def processing(self, name, frame, prediction):
        return self.process(name, frame, prediction)

def main(args, force=False):
    try:
        io_data.input_loop(args, DrawThread)
    except KeyboardInterrupt:
        pass
