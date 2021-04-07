from threading import Lock, Condition
import time
import json
from threading import Thread, Condition, Lock
from .workflow_abstraction import AbstractWorkflow
from .rpc_workflow import import_rpc_package, requires_deepomatic_rpc
from ..version import __title__, __version__
from ..exceptions import ResultInferenceError, ResultInferenceTimeout
try:
    import Queue as queue
except ImportError:
    import queue as queue

rpc, protobuf, grpc = import_rpc_package()

class gRPCStreamHandler(Thread):

    class Requests(object):
        def __init__(self, maxsize=0):
            self._queue = queue.Queue(maxsize=maxsize)
            self._running = False

        def __iter__(self):
            self._running = True
            return self

        def stop(self):
            self._running = False
        
        def put(self, request):
            self._queue.put(request)

        def __next__(self):
            while self._running:
                try:
                    return self._queue.get(timeout=1)
                except queue.Empty:
                    pass
            else:
                raise StopIteration

    class Future(object):
        def __init__(self):
            self.__condition = Condition(Lock())
            self.__val = None
            self.__is_set = False

        def result(self, timeout):
            with self.__condition:
                while not self.__is_set:
                    self.__condition.wait(timeout)
                return self.__val

        def set(self, val):
            with self.__condition:
                if self.__is_set:
                    raise RuntimeError("Future has already been set")
                self.__val = val
                self.__is_set = True
                self.__condition.notify_all()

        def done(self):
            return self.__is_set

    def __init__(self, stub):
        Thread.__init__(self)
        self._stub = stub
        self._lock = Lock()
        self._requests = self.Requests() # TODO: maxsize
        self._futures = queue.Queue() # TODO: maxsize

    def run(self):
        stream = self._stub.ExecuteWorkflowStream(iter(self._requests))
        try:
            for response in stream:
                future = self._futures.get()
                future.set(response)
        except grpc._channel._Rendezvous:
            self.stop()

    def stop(self):
        self._requests.stop()

    def send(self, request):
        with self._lock:
            self._requests.put(request)
            future = self.Future()
            self._futures.put(future)
            return future


@requires_deepomatic_rpc
class WorkflowServerRecognition(AbstractWorkflow):
    @requires_deepomatic_rpc
    class InferResult(AbstractWorkflow.AbstractInferResult):
        def __init__(self, input_name, future):
            self._input_name = input_name
            self._future = future

        def get_predictions(self, timeout):
            try:
                result = self._future.result(timeout)
                try:
                    flow_container = result.flow_container
                    workflow_result = flow_container.workflow_data[self._input_name]
                    outputs = []
                    predictions = {
                        'outputs': [{
                            'labels': {
                                'predicted': [{
                                    'label_id': prediction.label_id,
                                    'label_name': prediction.label_name,
                                    'score': prediction.score,
                                    'threshold': 0,
                                    'roi': protobuf.json_format.MessageToDict(region.roi,
                                                                            including_default_value_fields=True,
                                                                            preserving_proto_field_name=True)
                                } for region in workflow_result.regions
                                    for key, concept in region.concepts.items()
                                    for prediction in concept.predictions.predictions],
                                'discarded': []
                            }
                        }]
                    }
                    return predictions
                except rpc.exceptions.ServerError as e:
                    raise ResultInferenceError({'error': str(e), 'code': e.code})

            except grpc.FutureTimeoutError:
                raise ResultInferenceTimeout(timeout)

        def __str__(self):
            return '<{}>'.format(self.__class__.__qualname__)

    def __init__(self, workflow_server_url, is_stream=True, input_name='image_input', return_flow_container=True):
        super(WorkflowServerRecognition, self).__init__('workflow_server')
        self._id = 'workflow_server'
        self._input_name = input_name
        self._is_stream = is_stream
        self._return_flow_container = return_flow_container
        self._workflow_server_url = workflow_server_url
        self._channel = grpc.insecure_channel(self._workflow_server_url)
        self._stub = rpc.buffers.protobuf.workflows.WorkflowExecution_pb2_grpc.WorkflowExecutorStub(self._channel)
        if self._is_stream:
            self._stream = gRPCStreamHandler(self._stub)
            self._stream.start() # TODO: here ?

        # self.stream_name = stream_name
        self.camera_metadata = {} # TODO

    def close(self):
        if self._is_stream:
            self._stream.stop()

        if self._channel is not None:
           self._channel.close()
           self._channel = None
           self._stub = None
        

    def infer(self, encoded_image_bytes, _useless_push_client, _useless_frame_name):
        request = rpc.buffers.protobuf.workflows.WorkflowExecution_pb2.WorkflowRequest()
        request.workflow_entries[self._input_name].image = encoded_image_bytes
        request.return_flow_container = self._return_flow_container
        request.metadata['user-agent'] = "%s %s".format(__title__, __version__)
        request.metadata['type'] = 'camera'
        request.metadata['timestamp'] = str(time.time())
        request.metadata['camera'] = json.dumps(self.camera_metadata)
        request.output_routing_key = '' # TODO
        if self._is_stream:
            future = self._stream.send(request)
        else:
            future = self._stub.ExecuteWorkflow.future(request)
        return self.InferResult(self._input_name, future)
        
