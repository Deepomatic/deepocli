import logging
import cv2
from deepomatic.cli.workflow.workflow_abstraction import AbstractWorkflow
from deepomatic.cli.common import DeepoCLIException

can_use_rpc = True

try:
    from deepomatic.rpc.client import Client
except ImportError:
    can_use_rpc = False

if can_use_rpc:
    from deepomatic.rpc import v07_ImageInput, BINARY_IMAGE_PREFIX
    from deepomatic.rpc.helpers.v07_proto import create_recognition_command_mix
    from deepomatic.rpc.helpers.proto import create_v07_images_command
    from google.protobuf.json_format import MessageToDict


class RpcRecognition(AbstractWorkflow):

    class InferResult(AbstractWorkflow.AbstractInferResult):

        def __init__(self, correlation_id, consumer):
            self._correlation_id = correlation_id
            self._consumer = consumer

        def get(self):
            response = self._consumer.get(self._correlation_id, timeout=60)
            outputs = response.to_parsed_result_buffer()
            return {
                'outputs': [{
                    'labels': MessageToDict(output.labels, including_default_value_fields=True, preserving_proto_field_name=True)
                } for output in outputs]
            }

    def __init__(self, recognition_version_id, amqp_url, routing_key, recognition_cmd_kwargs=None):
        super(RpcRecognition, self).__init__('recognition_{}'.format(recognition_version_id))
        self._id = recognition_version_id

        self._routing_key = routing_key
        self._stream = None

        recognition_cmd_kwargs = recognition_cmd_kwargs or {}

        print(can_use_rpc)
        if can_use_rpc:
            self._client = Client(amqp_url)
            self._recognition = None
            try:
                recognition_version_id = int(recognition_version_id)
            except ValueError:
                raise DeepoCLIException("Cannot cast recognition ID into a number")

            self._command_mix = create_recognition_command_mix(recognition_version_id,
                                                               **recognition_cmd_kwargs)
            # We want to handle retrieve the response in the order we want
            self._stream = self._client.new_stream(self._routing_key, keep_response_order=False)

        else:
            self._client = None
            raise DeepoCLIException('RPC not available')

    def close(self):
        if self._stream is not None:
            self._stream.close()

    def infer(self, frame):
        _, buf = cv2.imencode('.jpeg', frame)
        image_input = v07_ImageInput(source=BINARY_IMAGE_PREFIX + buf.tobytes())
        # forward_to parameter can be removed for images of worker nn with tag >= 0.7.8
        serialized_buffer = create_v07_images_command([image_input], self._command_mix, forward_to=[self._stream.response_queue.name])
        correlation_id = self._stream.send_binary(serialized_buffer)
        return self.InferResult(correlation_id, self._stream.consumer)
