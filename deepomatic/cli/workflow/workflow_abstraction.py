import os


class AbstractWorkflow(object):
    class AbstractInferResult(object):
        def get_predictions(self):
            raise NotImplementedError()

        def __str__(self):
            return '<{}>'.format(self.__class__.__qualname__)

    def __init__(self, display_id):
        self._display_id = display_id

    def new_client(self):
        return None

    def close_client(self, client):
        pass

    def close(self):
        raise NotImplementedError()

    @property
    def display_id(self):
        return self._display_id

    def infer(self, encoded_image_bytes, push_client):
        """Should return a subclass of AbstractInferResult"""
        raise NotImplementedError()

    def get_json_output_filename(self, file):
        dirname = os.path.dirname(file)
        filename, _ = os.path.splitext(file)
        return os.path.join(dirname, filename + '.{}.json'.format(self.display_id))
