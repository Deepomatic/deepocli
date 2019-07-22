import json
from jsonschema import validate


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
                "required": ["location"],
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


def is_valid_json_with_schema(json_data, json_schema):
    """Validate a JSON using a schema"""
    try:
        validate(instance=json_data, schema=json_schema)
        return True
    except Exception:
        return False


def is_valid_studio_json(json_data):
    """Validate a JSON using the studio schema"""
    return is_valid_json_with_schema(json_data, STUDIO_JSON_SCHEMA)


def is_valid_vulcan_json(json_data):
    """Validate a JSON using the vulcan schema"""
    return is_valid_json_with_schema(json_data, VULCAN_JSON_SCHEMA)
