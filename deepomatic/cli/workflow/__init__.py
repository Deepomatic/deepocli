import logging
from .cloud_workflow import CloudRecognition
from .rpc_workflow import RpcRecognition
from .json_workflow import JsonRecognition


LOGGER = logging.getLogger(__name__)


def get_workflow(args):
    # Retrieve recognition arguments
    recognition_id = args.get('recognition_id')
    amqp_url = args.get('amqp_url')
    routing_key = args.get('routing_key')
    predict_from_json = args.get('predict_from_json')

    # Check whether we should use predictions from a json, rpc deployment or the cloud API
    if predict_from_json:
        LOGGER.debug('Using JSON workflow with recognition_id {}'.format(recognition_id))
        return JsonRecognition(recognition_id)
    elif all([recognition_id, amqp_url, routing_key]):
        LOGGER.debug('Using RPC workflow with recognition_id {}, amqp_url {} and routing_key {}'.format(recognition_id, amqp_url, routing_key))
        return RpcRecognition(recognition_id, amqp_url, routing_key)
    elif recognition_id:
        LOGGER.debug('Using Cloud workflow with recognition_id {}'.format(recognition_id))
        return CloudRecognition(recognition_id)
    LOGGER.error("Couldn't get workflow based on args {}".format(args))
    sys.exit(1)
