from .workflow_abstraction import AbstractWorkflow
from ..exceptions import ResultInferenceError, ResultInferenceTimeout
from ..exceptions import DeepoRPCRecognitionError, DeepoRPCUnavailableError


def import_rpc_package(should_raise=False):
    rpc, protobuf = None, None
    try:
        from deepomatic import rpc
    except ImportError:
        if should_raise:
            raise DeepoRPCUnavailableError('RPC not installed')

    try:
        from deepomatic.rpc import v07_ImageInput, BINARY_IMAGE_PREFIX  # noqa: F401
        from deepomatic.rpc.client import Client  # noqa: F401
        from deepomatic.rpc.exceptions import ServerError  # noqa: F401
        from deepomatic.rpc.amqp.exceptions import Timeout  # noqa: F401
        from deepomatic.rpc.response import wait_responses  # noqa: F401
        from deepomatic.rpc.helpers.v07_proto import create_recognition_command_mix  # noqa: F401
        from deepomatic.rpc.helpers.proto import create_v07_images_command  # noqa: F401
        from deepomatic.rpc.buffers.protobuf.cli.Message_pb2 import Message  # noqa: F401
        from google import protobuf  # noqa: F401
        import google.protobuf.json_format  # noqa: F401
    except ImportError as e:
        if should_raise:
            raise DeepoRPCUnavailableError('RPC not up-to-date: %s' % e)

    return rpc, protobuf


rpc, protobuf = import_rpc_package()


# decorator that prevents class instanciation when deepomatic rpc is not available
def requires_deepomatic_rpc(cls):
    def override_init(old_init):
        def __init__(self, *args, **kwargs):
            # checks that rpc is installed and up-to-date
            import_rpc_package(should_raise=True)
            try:
                old_init(self, *args, **kwargs)
            except Exception:
                old_init(self)

        return __init__
    cls.__init__ = override_init(cls.__init__)
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
                    predictions = {
                        'outputs': [
                            {
                                'labels': protobuf.json_format.MessageToDict(output.labels,
                                                                             including_default_value_fields=True,
                                                                             preserving_proto_field_name=True)
                            } for output in outputs
                        ]
                    }
                    return predictions
                except rpc.exceptions.ServerError as e:
                    raise ResultInferenceError({'error': str(e), 'code': e.code})
            except rpc.amqp.exceptions.Timeout:
                raise ResultInferenceTimeout(timeout)

        def __str__(self):
            return '<{} correlation_id={}>'.format(self.__class__.__qualname__, self._correlation_id)

    def __init__(self, recognition_version_id, amqp_url, routing_key, recognition_cmd_kwargs=None):
        super(RpcRecognition, self).__init__('recognition_{}'.format(recognition_version_id))
        self._id = recognition_version_id

        self._routing_key = routing_key
        self._consumer = None
        self.amqp_url = amqp_url

        # We declare the client that will be used for consuming in one thread only
        # RPC client is not thread safe
        self._consume_client = rpc.client.Client(amqp_url)
        if recognition_version_id is None:
            self._command_mix = rpc.helpers.v07_proto.create_workflow_command_mix()
        else:
            recognition_cmd_kwargs = recognition_cmd_kwargs or {'show_discarded': True, 'max_predictions': 1000}

            try:
                recognition_version_id = int(recognition_version_id)
            except ValueError:
                raise DeepoRPCRecognitionError("Cannot cast recognition ID into a number")

            self._command_mix = rpc.helpers.v07_proto.create_recognition_command_mix(recognition_version_id,
                                                                                     **recognition_cmd_kwargs)
        self._command_queue = self._consume_client.new_queue(self._routing_key)
        self._response_queue, self._consumer = self._consume_client.new_consuming_queue()

    def close_client(self, client):
        client.amqp_client.ensured_connection.close()

    def new_client(self):
        # Allow to create multiple clients for threads that will push
        # Since RPC client is not thread safe
        return rpc.client.Client(self.amqp_url)

    def close(self):
        if self._consumer is not None:
            self._consume_client.remove_consuming_queue(self._response_queue, self._consumer)
        self.close_client(self._consume_client)

    def infer(self, encoded_image_bytes, push_client, _useless_frame_name):
        # _useless_frame_name is used for the json workflow
        image_input = rpc.v07_ImageInput(source=rpc.BINARY_IMAGE_PREFIX + encoded_image_bytes)
        # forward_to parameter can be removed for images of worker nn with tag >= 0.7.8
        reply_to = self._response_queue.name
        serialized_buffer = rpc.helpers.proto.create_v07_images_command([image_input], self._command_mix, forward_to=[reply_to])
        correlation_id = push_client.send_binary(serialized_buffer, self._command_queue.name, reply_to=reply_to)
        return self.InferResult(correlation_id, self._consumer)
