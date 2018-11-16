import os
import logging
import datetime
import deepomatic
import cv2
from deepomatic.exceptions import TaskTimeout, TaskError

import deepoctl.common as common

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
            except (TaskTimeout, TaskError) as e:
                return None

    def __init__(self, recognition_version_id):
        super(CloudRecognition, self).__init__('r{}'.format(recognition_version_id))
        self._id = recognition_version_id

        app_id = os.getenv('DEEPOMATIC_APP_ID', None)
        api_key = os.getenv('DEEPOMATIC_API_KEY', None)
        if app_id is None or api_key is None:
            raise common.DeepoCTLException('Please define the environment variables DEEPOMATIC_APP_ID and DEEPOMATIC_API_KEY to use cloud-based recognition models.')
        self._client = deepomatic.Client(app_id, api_key)
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
        return self.InferResult(self._model.inference(inputs=[deepomatic.ImageInput(buf.tobytes(), encoding="binary")], return_task=True, wait_task=False))

# ---------------------------------------------------------------------------- #

class RpcRecognition(AbstractWorkflow):
    from worker_nn.client import Client, BINARY_IMAGE_PREFIX, has_labels, has_scalar, Result, CallbackCache
    from worker_nn.buffers.protobuf.nn.v07.Inputs_pb2 import ImageInput, Inputs
    from worker_nn.buffers.protobuf.common.Image_pb2 import BBox

    class InferResult(AbstractWorkflow.AbstractInferResult):
        from google.protobuf.json_format import MessageToDict

        def __init__(self, async_res):
            self._async_res = async_res

        def get(self):
            outputs = self._async_res.get_parsed_result()
            return {
                'outputs': [{
                    'labels': self.MessageToDict(output.labels, including_default_value_fields=True, preserving_proto_field_name=True)
                } for output in outputs]
            }

    def __init__(self, recognition_version_id, amqp_url, routing_key):
        super(RpcRecognition, self).__init__('recognition_{}'.format(recognition_version_id))
        self._id = recognition_version_id

        self._amqp_url = amqp_url
        self._routing_key = routing_key
        self._client = self.Client(self._amqp_url, max_callback=4)
        self._recognition = None
        try:
            recognition_version_id = int(recognition_version_id)
            self._recognition = self._client.create_recognition(version_id=recognition_version_id)
        except ValueError:
            logging.warning("Cannot cast recognition ID into a number")

    def infer(self, frame):
        _, buf = cv2.imencode('.jpeg', frame)
        image = self.ImageInput(source=self.BINARY_IMAGE_PREFIX + buf.tobytes(), crop_uniform_background=False)
        inputs = self.Inputs(inputs=[self.Inputs.InputMix(image=image)])
        return self.InferResult(self._client.recognize(self._routing_key, self._recognition, inputs))

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
