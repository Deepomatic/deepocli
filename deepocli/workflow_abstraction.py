import os
import logging
import datetime
import cv2
import deepomatic.api.client
import deepomatic.api.inputs
import deepomatic.api.exceptions

import deepocli.common as common


can_use_rpc = True

try:
    import deepomatic.rpc
    import deepomatic.rpc.client
    from deepomatic.rpc import v07_ImageInput
    from deepomatic.rpc.response import wait
    from deepomatic.rpc.helpers.v07_proto import (create_images_input_mix, create_recognition_command_mix)
    from google.protobuf.json_format import MessageToDict
except ImportError:
    can_use_rpc = False


class AbstractWorkflow(object):
    class AbstractInferResult(object):
        def get(self):
            raise NotImplementedError

    def __init__(self, display_id):
        self._display_id = display_id

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

# ---------------------------------------------------------------------------- #

class RpcRecognition(AbstractWorkflow):

    class InferResult(AbstractWorkflow.AbstractInferResult):

        def __init__(self, correlation_id, consumer):
            self._correlation_id = correlation_id
            self._consumer = consumer

        def get(self):
            response = wait(self._consumer, self._correlation_id, timeout=60)
            outputs = response.to_parsed_buffer_result()
            return {
                'outputs': [{
                    'labels': MessageToDict(output.labels, including_default_value_fields=True, preserving_proto_field_name=True)
                } for output in outputs]
            }

    def __init__(self, recognition_version_id, amqp_url, routing_key):
        super(RpcRecognition, self).__init__('recognition_{}'.format(recognition_version_id))
        self._id = recognition_version_id

        self._amqp_url = amqp_url
        self._routing_key = routing_key
        self._response_routing_key = routing_key + '.responses'

        if can_use_rpc:
            self._client = deepomatic.rpc.client.Client(self._amqp_url)
            self._recognition = None
            try:
                recognition_version_id = int(recognition_version_id)
                self._command_mix = create_recognition_command_mix(recognition_version_id)
                command_queue, response_queue, self._consumer = self._client.add_rpc_queues(routing_key, response_queue_name=self._response_routing_key)
            except ValueError:
                logging.error("Cannot cast recognition ID into a number")
            except Exception:
                logging.exception("Error creating RPC client")

        else:
            self._client = None
            logging.error('RPC not available')

    def infer(self, frame):
        if (self._client is not None and frame is not None):
            _, buf = cv2.imencode('.jpeg', frame)
            image_input = v07_ImageInput(source=deepomatic.rpc.BINARY_IMAGE_PREFIX + buf.tobytes())
            input_mix = create_images_input_mix([image_input])
            correlation_id = self._client.command(self._routing_key, self._command_mix, input_mix, [self._response_routing_key])
            return self.InferResult(correlation_id, self._consumer)
        else:
            logging.error('RPC not available')
            return {
                'outputs': []
            }
# ---------------------------------------------------------------------------- #

def get_workflow(args):
    recognition_id = args.get('recognition_id', None)
    amqp_url = args.get('amqp_url', None)
    routing_key = args.get('routing_key', None)

    if all([recognition_id, amqp_url, routing_key]):
        workflow = RpcRecognition(recognition_id, amqp_url, routing_key)
    elif recognition_id:
        workflow = CloudRecognition(recognition_id)
    else:
        return None
    return workflow