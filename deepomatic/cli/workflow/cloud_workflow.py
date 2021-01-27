import logging
from .workflow_abstraction import AbstractWorkflow
from ..exceptions import (SendInferenceError,
                          ResultInferenceError,
                          ResultInferenceTimeout)
from .. import exceptions
import deepomatic.api.client
import deepomatic.api.inputs
from ..version import __title__, __version__
from tenacity import stop_never
from deepomatic.api.exceptions import TaskError, TaskTimeout, BadStatus, DeepomaticException

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

        def __str__(self):
            return '<{} task_id={}>'.format(self.__class__.__qualname__, self._task.pk)

    def close(self):
        self._client.http_helper.session.close()

    def __init__(self, recognition_version_id):
        super(CloudRecognition, self).__init__('r{}'.format(recognition_version_id))
        self._id = recognition_version_id

        # Retry indefinitely until the API is available
        http_retry = deepomatic.api.http_retry.HTTPRetry(stop=stop_never)

        user_agent_prefix = '{}/{}'.format(__title__, __version__)
        try:
            self._client = deepomatic.api.client.Client(user_agent_prefix=user_agent_prefix,
                                                        http_retry=http_retry)
        except DeepomaticException:  # TODO later replace with CredentialsNotFound
            error = ('Credentials not found.'
                     ' Please define the DEEPOMATIC_API_KEY environment variable to use cloud-based recognition models.')
            raise exceptions.DeepoCLICredentialsError(error)

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
