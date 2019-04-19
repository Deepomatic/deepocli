from .cloud_workflow import CloudRecognition
from .rpc_workflow import RpcRecognition


def get_workflow(args):
    recognition_id = args['recognition_id']
    amqp_url = args.get('amqp_url')
    routing_key = args.get('routing_key')

    if all([recognition_id, amqp_url, routing_key]):
        return RpcRecognition(recognition_id, amqp_url, routing_key)
    elif recognition_id:
        return CloudRecognition(recognition_id)
    raise Exception("Couldn't get workflow based on args {}".format(args))
