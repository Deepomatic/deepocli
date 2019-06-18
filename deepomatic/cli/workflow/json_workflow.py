from .workflow_abstraction import AbstractWorkflow


class JsonRecognition(AbstractWorkflow):

    def __init__(self, recognition_version_id):
        super(JsonRecognition, self).__init__('r{}'.format(recognition_version_id))
        self._id = recognition_version_id

    def close(self):
        pass
