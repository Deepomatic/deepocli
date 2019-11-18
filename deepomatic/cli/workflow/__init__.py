import logging
import sys
import json
from .workflow_abstraction import AbstractWorkflow
from .cloud_workflow import CloudRecognition
from .rpc_workflow import RpcRecognition, requires_deepomatic_rpc, import_rpc_package
from .json_workflow import JsonRecognition
from ..exceptions import DeepoWorkflowError, DeepoCLICredentialsError


LOGGER = logging.getLogger(__name__)


def get_workflows(args):
    try:
        # Retrieve recognition arguments
        recognition_id = args.get('recognition_id')
        amqp_url = args.get('amqp_url')
        routing_key = args.get('routing_key')
        pred_from_file = args.get('pred_from_file')
        threshold = args.get('threshold')
        inference_fps = args.get('inference_fps', float('inf'))
        file = args.get('file')

        # Check whether we should use predictions from a json, rpc deployment or the cloud API
        if file:
            with open(file, 'r') as f:
                workflows = json.load(f)
                return [workflow for args in workflows for workflow in get_workflows(args)]
        elif pred_from_file:
            LOGGER.debug('Using JSON workflow with recognition_id {}'.format(recognition_id))
            return [JsonRecognition(recognition_id, pred_from_file, threshold)]
        elif all([amqp_url, routing_key]):
            LOGGER.debug('Using RPC workflow with recognition_id {}, amqp_url {} and routing_key {}'.format(recognition_id, amqp_url, routing_key))
            return [RpcRecognition(recognition_id, amqp_url, routing_key, threshold=threshold, inference_fps=inference_fps)]
        elif recognition_id:
            LOGGER.debug('Using Cloud workflow with recognition_id {}'.format(recognition_id))
            return [CloudRecognition(recognition_id, threshold=threshold, inference_fps=inference_fps)]
        else:
            raise DeepoWorkflowError("Couldn't get workflow based on args {}".format(args))
    except (DeepoCLICredentialsError, DeepoWorkflowError) as e:
        LOGGER.error(str(e))
        sys.exit(1)
