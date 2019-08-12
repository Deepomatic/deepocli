import cv2
import time
import logging
from .workflow_abstraction import AbstractWorkflow
from ..exceptions import ResultInferenceError, ResultInferenceTimeout
from ..exceptions import DeepoRPCRecognitionError, DeepoRPCUnavailableError


# decorator that prevents class instanciation when deepomatic rpc is not available
def requires_deepomatic_rpc(cls):
    def override_new(old_new):
        def __new__(cls, *args, **kwargs):
            # First we test whether the deepomatic-rpc module is installed. An error here indicates we need to install it.
            try:
                from deepomatic import rpc
            except ImportError:
                raise DeepoRPCUnavailableError('RPC not available')
            # If the deepomatic-rpc module is installed, then we try to import the other modules. An error here might indicate a
            # version mismatch, in which case we want to know which one and why, i.e. we don't want to catch the error but we want
            # to display it to the end user.
            try:
                from deepomatic.rpc import v07_ImageInput, BINARY_IMAGE_PREFIX
                from deepomatic.rpc.exceptions import ServerError
                from deepomatic.rpc.amqp.exceptions import Timeout
                from deepomatic.rpc.response import wait_responses
                from deepomatic.rpc.helpers.v07_proto import create_recognition_command_mix
                from deepomatic.rpc.helpers.proto import create_v07_images_command
            except ImportError as e:
                raise DeepoRPCUnavailableError('RPC version mismatch: %s' % e)

            try:
                return old_new(cls, *args, **kwargs)
            except:
                return old_new(cls)

        return __new__
    cls.__new__ = override_new(cls.__new__)
    return cls

@requires_deepomatic_rpc
class RpcRecognition(AbstractWorkflow):
    @requires_deepomatic_rpc
    class InferResult(AbstractWorkflow.AbstractInferResult):
        def __init__(self, correlation_id, consumer):
            self._correlation_id = correlation_id
            self._consumer = consumer

        def get_predictions(self, timeout):
            try:
                response = self._consumer.get(self._correlation_id, timeout=timeout)
                try:
                    outputs = response.to_parsed_result_buffer()
                    predictions = {'outputs': [{'labels': MessageToDict(output.labels, including_default_value_fields=True, preserving_proto_field_name=True)} for output in outputs]}
                    return predictions
                except ServerError as e:
                    raise ResultInferenceError({'error': str(e), 'code': e.code})
            except Timeout:
                raise ResultInferenceTimeout(timeout)

    def __init__(self, recognition_version_id, amqp_url, routing_key, recognition_cmd_kwargs=None):
        super(RpcRecognition, self).__init__('recognition_{}'.format(recognition_version_id))
        self._id = recognition_version_id

        self._routing_key = routing_key
        self._consumer = None
        self.amqp_url = amqp_url

        recognition_cmd_kwargs = recognition_cmd_kwargs or {'show_discarded': True, 'max_predictions': 1000}

        # We declare the client that will be used for consuming in one thread only
        # RPC client is not thread safe
        self._consume_client = Client(amqp_url)
        self._recognition = None
        try:
            recognition_version_id = int(recognition_version_id)
        except ValueError:
            raise DeepoRPCRecognitionError("Cannot cast recognition ID into a number")

        self._command_mix = create_recognition_command_mix(recognition_version_id,
                                                            **recognition_cmd_kwargs)
        self._command_queue = self._consume_client.new_queue(self._routing_key)
        self._response_queue, self._consumer = self._consume_client.new_consuming_queue()


    def close_client(self, client):
        client.amqp_client.ensured_connection.close()

    def new_client(self):
        # Allow to create multiple clients for threads that will push
        # Since RPC client is not thread safe
        return Client(self.amqp_url)

    def close(self):
        if self._consumer is not None:
            self._consume_client.remove_consuming_queue(self._response_queue, self._consumer)
        self.close_client(self._consume_client)

    def infer(self, encoded_image_bytes, push_client, _useless_frame_name):
        # _useless_frame_name is used for the json workflow
        image_input = v07_ImageInput(source=BINARY_IMAGE_PREFIX + encoded_image_bytes)
        # forward_to parameter can be removed for images of worker nn with tag >= 0.7.8
        reply_to = self._response_queue.name
        serialized_buffer = create_v07_images_command([image_input], self._command_mix, forward_to=[reply_to])
        correlation_id = push_client.send_binary(serialized_buffer, self._command_queue.name, reply_to=reply_to)
        return self.InferResult(correlation_id, self._consumer)
