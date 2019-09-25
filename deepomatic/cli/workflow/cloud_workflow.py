import os
import sys
import logging
from .workflow_abstraction import AbstractWorkflow,
from ..exceptions import (SendInferenceError,
                          ResultInferenceError
                          ResultInferenceTimeout)
from .. import common, exceptions
import deepomatic.api.client
import deepomatic.api.inputs
from ..version import __title__, __version__
from tenacity import stop_never
from deepomatic.api.exceptions import TaskError, TaskTimeout, BadStatus

LOGGER = logging.getLogger(__name__)


class CloudRecognition(AbstractWorkflow):

    class InferResult(AbstractWorkflow.AbstractInferResult):
        def __init__(self, task):
            self._task = task

        def get_predictions(self, timeout):
            try:
                self._task.wait(timeout=timeout)
                return self._task['data']
            except BadStatus as e:
                # HTTP Error
                raise ResultInferenceError(e)
            except TaskError:
                # Task is in error
                raise ResultInferenceError(self._task.data())
            except TaskTimeout:
                # Task did not finish on time
                raise ResultInferenceTimeout(timeout)


    def close(self):
        self._client.http_helper.session.close()

    def __init__(self, recognition_version_id):
        super(CloudRecognition, self).__init__('r{}'.format(recognition_version_id))
        self._id = recognition_version_id

        app_id = os.getenv('DEEPOMATIC_APP_ID', None)
        api_key = os.getenv('DEEPOMATIC_API_KEY', None)
        if app_id is None or api_key is None:
            error = 'Credentials not found. Please define the DEEPOMATIC_APP_ID and DEEPOMATIC_API_KEY environment variables to use cloud-based recognition models.'
            raise exceptions.DeepoCLICredentialsError(error)

        # Retry indefinitely until the API is available
        http_retry = deepomatic.api.http_retry.HTTPRetry(stop=stop_never)

        user_agent_prefix = '{}/{}'.format(__title__, __version__)
        self._client = deepomatic.api.client.Client(app_id, api_key,
                                                    user_agent_prefix=user_agent_prefix,
                                                    http_retry=http_retry)
        self._model = None
        try:
            recognition_version_id = int(recognition_version_id)
        except ValueError:
            LOGGER.warning("Cannot cast recognition ID into a number, trying with a public recognition model")
            self._model = self._client.RecognitionSpec.retrieve(recognition_version_id)
        if self._model is None:
            self._model = self._client.RecognitionVersion.retrieve(recognition_version_id)

    def infer(self, encoded_image_bytes, _useless_push_client, _useless_frame_name):
        # _useless_push_client and _useless_frame_name are used for the rpc and json workflows
        try:
            return self.InferResult(self._model.inference(
                inputs=[deepomatic.api.inputs.ImageInput(encoded_image_bytes, encoding="binary")],
                show_discarded=True,
                return_task=True,
                wait_task=False))
        except BadStatus as e:
            # HTTP error
            raise SendInferenceError(e)
