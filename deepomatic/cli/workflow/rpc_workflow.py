import logging
import cv2
from deepocli.workflow.workflow_abstraction import AbstractWorkflow

can_use_rpc = True

try:
    from deepomatic.rpc.client import Client
    from deepomatic.rpc import v07_ImageInput, BINARY_IMAGE_PREFIX
    from deepomatic.rpc.response import wait
    from deepomatic.rpc.helpers.v07_proto import (create_images_input_mix, create_recognition_command_mix)
    from google.protobuf.json_format import MessageToDict
except ImportError:
    can_use_rpc = False


class RpcRecognition(AbstractWorkflow):

    class InferResult(AbstractWorkflow.AbstractInferResult):

        def __init__(self, correlation_id, consumer):
            self._correlation_id = correlation_id
            self._consumer = consumer

        def get(self):
            response = wait(self._consumer, self._correlation_id, timeout=60)
            outputs = response.to_parsed_result_buffer()
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
            self._client = Client(self._amqp_url)
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
