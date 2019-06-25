import sys
import json
import logging
from .workflow_abstraction import AbstractWorkflow, InferenceError
from ..json_schema import validate_studio_json, validate_vulcan_json
from ..cmds.studio_helpers.vulcan2studio import transform_json_from_studio_to_vulcan


LOGGER = logging.getLogger(__name__)


class JsonRecognition(AbstractWorkflow):

    class InferResult(AbstractWorkflow.AbstractInferResult):
        def __init__(self, frame_name, frame_pred):
            self.frame_name = frame_name
            self.frame_pred = frame_pred

        def get_predictions(self, timeout):
            return self.frame_pred

    def __init__(self, recognition_version_id, pred_file):
        super(JsonRecognition, self).__init__('r{}'.format(recognition_version_id))
        self._id = recognition_version_id
        self._pred_file = pred_file

        # Check json validity
        if not(validate_studio_json(pred_file)) and not(validate_vulcan_json(pred_file)):
            LOGGER.error("Prediction JSON file {} is neither a proper Studio or Vulcan JSON file".format(pred_file))
        # Load json
        with open(pred_file) as json_file:
            vulcan_json_with_pred = json.load(json_file)
        # Transform it to vulcan format if needed
        if validate_vulcan_json(pred_file):
            LOGGER.debug("Vulcan prediction JSON {} validated".format(pred_file))
        if validate_studio_json(pred_file):
            vulcan_json_with_pred = transform_json_from_studio_to_vulcan(vulcan_json_with_pred)
            LOGGER.debug("Studio prediction JSON {} validated and transformer to Vulcan format".format(pred_file))

        # Store predictions for easy access
        self._all_predictions = {vulcan_pred['location']: vulcan_pred for vulcan_pred in vulcan_json_with_pred}

    def close(self):
        pass

    def infer(self, _useless_encoded_image_bytes, _useless_push_client, frame_name):
        # _useless_encoded_image_bytes and _useless_push_client are used only for rpc and cloud workflows
        try:
            frame_pred = self._all_predictions[frame_name]
        except:
            raise InferenceError("Could not find predictions for frame {}".format(frame_name))

        return self.InferResult(frame_name, frame_pred)
