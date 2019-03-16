import os


class AbstractWorkflow(object):
    class AbstractInferResult(object):
        def get_predictions(self):
            raise NotImplementedError

    def __init__(self, display_id):
        self._display_id = display_id

    def close(self):
        pass

    @property
    def display_id(self):
        return self._display_id

    def infer(self, frame):
        """Should return a subclass of AbstractInferResult"""
        raise NotImplemented

    def get_json_output_filename(self, file):
        dirname = os.path.dirname(file)
        filename, ext = os.path.splitext(file)
        return os.path.join(dirname, filename + '.{}.json'.format(self.display_id))
