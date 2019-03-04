import os
import logging
import cv2
from deepomatic.cli.workflow.workflow_abstraction import AbstractWorkflow
from deepomatic.cli import common
import deepomatic.api.client
import deepomatic.api.inputs
import deepomatic.api.exceptions


class CloudRecognition(AbstractWorkflow):
    class InferResult(AbstractWorkflow.AbstractInferResult):
        def __init__(self, task):
            self._task = task

        def get(self):
            try:
                return self._task.wait().data()['data']
            except (deepomatic.api.exceptions.TaskTimeout, deepomatic.api.exceptions.TaskError) as e:
                return None

    def __init__(self, recognition_version_id):
        super(CloudRecognition, self).__init__('r{}'.format(recognition_version_id))
        self._id = recognition_version_id

        app_id = os.getenv('DEEPOMATIC_APP_ID', None)
        api_key = os.getenv('DEEPOMATIC_API_KEY', None)
        if app_id is None or api_key is None:
            error = 'Please define the environment variables DEEPOMATIC_APP_ID and DEEPOMATIC_API_KEY to use cloud-based recognition models.'
            logging.error(error)
            raise common.DeepoCLIException(error)
        self._client = deepomatic.api.client.Client(app_id, api_key)
        self._model = None
        try:
            recognition_version_id = int(recognition_version_id)
        except ValueError:
            logging.warning("Cannot cast recognition ID into a number, trying with a public recognition model")
            self._model = self._client.RecognitionSpec.retrieve(recognition_version_id)
        if self._model is None:
            self._model = self._client.RecognitionVersion.retrieve(recognition_version_id)

    def infer(self, frame):
        _, buf = cv2.imencode('.jpeg', frame)
        return self.InferResult(self._model.inference(inputs=[deepomatic.api.inputs.ImageInput(buf.tobytes(), encoding="binary")], return_task=True, wait_task=False))
