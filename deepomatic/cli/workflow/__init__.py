from cloud_workflow import CloudRecognition
from rpc_workflow import RpcRecognition


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
