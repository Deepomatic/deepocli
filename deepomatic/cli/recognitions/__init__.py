import logging
from .cloud_recognition import CloudRecognition
from .rpc_recognition import RpcRecognition
from .json_recognition import JsonRecognition
from ..exceptions import DeepoRecognitionError


LOGGER = logging.getLogger(__name__)


def get_recognition(args):
    # Retrieve recognition arguments
    recognition_id = args.get('recognition_id')
    amqp_url = args.get('amqp_url')
    routing_key = args.get('routing_key')
    pred_from_file = args.get('pred_from_file')
    model_command = args.get('model_command')

    # Check whether we should use predictions from a json, rpc deployment or the cloud API
    if pred_from_file:
        LOGGER.debug('Using JSON recognition with recognition_id {}'.format(recognition_id))
        return JsonRecognition(recognition_id, pred_from_file)
    elif all([amqp_url, routing_key]):
        LOGGER.debug('Using RPC recognition with'
                     ' recognition_id {}, amqp_url {} and routing_key {}'.format(recognition_id, amqp_url, routing_key))
        return RpcRecognition(recognition_id, amqp_url, routing_key)
    elif recognition_id:
        LOGGER.debug('Using Cloud recognition with recognition_id {}'.format(recognition_id))
        return CloudRecognition(recognition_id)
    elif model_command == 'noop':
        return None
    else:
        raise DeepoRecognitionError("Couldn't get recognition based on args {}".format(args))


__all__ = ["get_recognition"]
