from deepomatic.cli.cmds import infer
from deepomatic.cli import io_data


class BlurThread(infer.InferenceThread):
    def __init__(self, worker_queue, output_queue, workflow, workflow_lock, **kwargs):
        super(BlurThread, self).__init__(worker_queue, output_queue, workflow, workflow_lock, **kwargs)
        self.process = io_data.BlurOutputData(**kwargs)

    def processing(self, name, frame, prediction):
        return self.process(name, frame, prediction)


def main(args, force=False):
    try:
        io_data.input_loop(args, BlurThread)
    except KeyboardInterrupt:
        pass
