import json
import logging
from .workflow_abstraction import AbstractWorkflow
from ..json_schema import validate_json, JSONSchemaType
from ..cmds.studio_helpers.vulcan2studio import transform_json_from_studio_to_vulcan
from ..exceptions import DeepoPredictionJsonError, DeepoOpenJsonError, SendInferenceError


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

        # Load the json
        try:
            with open(pred_file) as json_file:
                vulcan_json_with_pred = json.load(json_file)
        except Exception:
            raise DeepoOpenJsonError("Prediction JSON file {} is not a valid JSON file".format(pred_file))

        # Check json validity
        is_valid, error, schema_type = validate_json(vulcan_json_with_pred)
        if is_valid:
            if schema_type == JSONSchemaType.VULCAN:
                LOGGER.debug("Vulcan prediction JSON {} validated".format(pred_file))
            elif schema_type == JSONSchemaType.STUDIO:
                vulcan_json_with_pred = transform_json_from_studio_to_vulcan(vulcan_json_with_pred)
                LOGGER.debug("Studio prediction JSON {} validated and transformed to Vulcan format".format(pred_file))
        elif error is not None:
            LOGGER.warning("Error with {} JSON : {} in the instance {}".format(schema_type, error.message, list(error.path)))
            raise DeepoPredictionJsonError("Upload JSON file {} is not a proper {} JSON file".format(pred_file, schema_type))
        else:
            raise DeepoPredictionJsonError("Prediction JSON file {} is neither a proper Studio or Vulcan JSON file".format(pred_file))

        # Store predictions for easy access
        self._all_predictions = {vulcan_pred['data']['framename']: vulcan_pred for vulcan_pred in vulcan_json_with_pred}

    def close(self):
        pass

    def infer(self, _useless_encoded_image_bytes, _useless_push_client, frame_name):
        # _useless_encoded_image_bytes and _useless_push_client are used only for rpc and cloud workflows
        try:
            frame_pred = self._all_predictions[frame_name]
        except KeyError:
            raise SendInferenceError("Could not find predictions for frame {}".format(frame_name))

        return self.InferResult(frame_name, frame_pred)
