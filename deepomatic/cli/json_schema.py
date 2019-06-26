import os
import sys
import json
import logging
from jsonschema import validate


LOGGER = logging.getLogger(__name__)


# Define the vulcan json schema
VULCAN_ANNOTATION_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "roi": {},
            "score": {},
            "label_id": {},
            "threshold": {},
            "label_name": {}
        }
    }
}
VULCAN_JSON_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "required": ["outputs"],
        "properties": {
            "location": {"type": "string"},
            "outputs": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["labels"],
                    "properties": {
                        "labels": {
                            "type": "object",
                            "properties": {
                                "discarded": VULCAN_ANNOTATION_SCHEMA,
                                "predicted": VULCAN_ANNOTATION_SCHEMA
                            }
                        }
                    }
                }
            }
        }
    }
}

# Define the studio json format
STUDIO_JSON_SCHEMA = {
    "type": "object",
    "required": ["tags", "images"],
    "properties": {
        "tags": {
            "type": "array",
            "items": {"type": "string"}
        },
        "images": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["location", "annotated_regions"],
                "properties": {
                    "location": {"type": "string"},
                    "data": {"type": "object"},
                    "annotated_regions": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["tags", "region_type"],
                            "properties": {
                                "tags": {
                                    "type": "array",
                                    "items": {"type": "string"}
                                },
                                "region_type": {
                                    "type": "string",
                                    "enum": ["Box", "Whole"]
                                },
                                "score": {"type": "number"},
                                "threshold": {"type": "number"},
                                "region": {
                                    "type": "object",
                                    "required": ["xmin", "xmax", "ymin", "ymax"],
                                    "properties": {
                                        "xmin": {"type": "number"},
                                        "xmax": {"type": "number"},
                                        "ymin": {"type": "number"},
                                        "ymax": {"type": "number"}
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}


def validate_json(json_path, json_schema):
    """Validate a JSON using a schema"""
    # Check if the file exists
    if not os.path.isfile(json_path):
        LOGGER.error('File {} does not exists')
        return False

    # Load the file as a json
    try:
        with open(json_path) as json_file:
            json_data = json.load(json_file)
    except Exception as e:
        LOGGER.error('File {} could not be loaded as JSON: {}'.format(json_path, e))
        return False

    # Test json schema
    try:
        validate(instance=json_data, schema=json_schema)
        return True
    except:
        return False


def validate_studio_json(json_path):
    """Validate a JSON using the studio schema"""
    return validate_json(json_path, STUDIO_JSON_SCHEMA)


def validate_vulcan_json(json_path):
    """Validate a JSON using the vulcan schema"""
    return validate_json(json_path, VULCAN_JSON_SCHEMA)


if __name__ == '__main__':
    json_path = sys.argv[1]
    LOGGER.info("Studio json validity: {}".format(validate_studio_json(json_path)))
    LOGGER.info("Vulcan json validity: {}".format(validate_vulcan_json(json_path)))
