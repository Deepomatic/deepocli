import sys
import json
from jsonschema import validate


# Define the vulcan json schema
VULCAN_ANNOTATION_SCHEMA = {
    "$schema": "http://json-schema.org/schema#",
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
    "$schema": "http://json-schema.org/schema#",
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
    "$schema": "http://json-schema.org/schema#",
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


def test_json_format(json_path):
    """Find the proper json format."""
    # Try to load the file as a json
    try:
        with open(json_path) as json_file:
            json_data = json.load(json_file)
    except Exception as e:
        print('File {} could not be loaded as JSON: {}'.format(json_path, e))
        sys.exit(1)

    # Test vulcan json
    try:
        validate(instance=json_data, schema=VULCAN_JSON_SCHEMA)
        print('JSON {} is a valid vulcan JSON'.format(json_path))
    except:
        print('JSON {} is not a valid vulcan JSON'.format(json_path))

    # Test studio json
    try:
        validate(instance=json_data, schema=STUDIO_JSON_SCHEMA)
        print('JSON {} is a valid studio JSON'.format(json_path))
    except:
        print('JSON {} is not a valid studio JSON'.format(json_path))


if __name__ == '__main__':
    test_json_format(sys.argv[1])
