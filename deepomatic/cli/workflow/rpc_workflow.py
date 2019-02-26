import logging
import cv2
from deepocli.workflow.workflow_abstraction import AbstractWorkflow

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


class RpcRecognition(AbstractWorkflow):

    class InferResult(AbstractWorkflow.AbstractInferResult):

        def __init__(self, async_res):
            self._async_res = async_res

        def get(self):
            outputs = self._async_res.get_parsed_result()
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

        if can_use_rpc:
            self._client = deepomatic.rpc.client.Client(self._amqp_url, max_callback=4)
            self._recognition = None
            try:
                recognition_version_id = int(recognition_version_id)
                self._recognition = self._client.create_recognition(version_id=recognition_version_id)
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
            image = RPCImageInput(source=deepomatic.rpc.client.BINARY_IMAGE_PREFIX + buf.tobytes(), crop_uniform_background=False)
            inputs = RPCInputs(inputs=[RPCInputs.InputMix(image=image)])
            return self.InferResult(self._client.recognize(self._routing_key, self._recognition, inputs))
        else:
            logging.error('RPC not available')
            return {
                'outputs': []
            }
