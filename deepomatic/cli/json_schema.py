from jsonschema import validate, ValidationError


class JSONSchemaType:
    STUDIO = 'Studio'
    VULCAN = 'Vulcan'
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
        "required": ["tags"],
        "anyOf": [
            {"required": ["images"]},
            {"required": ["videos"]}
        ],
        "additionalProperties": False,
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
                    "additionalProperties": False,
                    "properties": {
                        "location": {"type": "string"},
                        "data": {"type": "object"},
                        "stage": {
                            "type": "string",
                            "enum": ["train", "val"]
                        },
                        "annotated_regions": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "required": ["tags", "region_type"],
                                "additionalProperties": False,
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
                                            "xmin": {"type": "number", "minimum": 0, "maximum": 1},
                                            "xmax": {"type": "number", "minimum": 0, "maximum": 1},
                                            "ymin": {"type": "number", "minimum": 0, "maximum": 1},
                                            "ymax": {"type": "number", "minimum": 0, "maximum": 1}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "videos": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["location"],
                    "properties": {
                        "location": {"type": "string"},
                        "data": {"type": "object"},
                        "stage": {
                            "type": "string",
                            "enum": ["train", "val"]
                        },
                        "preprocessing": {
                            "type": "object",
                            "properties": {
                                "fps": {"type": "number", "minimum": 1},
                                "start_time": {"type": "string"},
                                "end_time": {"type": "string"}
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


def validate_json(json_data):
    """
    Validate a JSON using the Studio and Vulcan schema
    Returns:
    - is_valid: True if the JSON is valid
    - error: ValidationError raised if not valid
    - schema_type: Studio or Vulcan, or None if both schema raise an error at the root of the JSON
    """
    is_valid = False
    error = None
    schema_type = None
    schema_dict = {JSONSchemaType.STUDIO: JSONSchemaType.STUDIO_JSON_SCHEMA,
                   JSONSchemaType.VULCAN: JSONSchemaType.VULCAN_JSON_SCHEMA}
    for schema_name, json_schema in schema_dict.items():
        try:
            validate(instance=json_data, schema=json_schema)
            is_valid = True
            schema_type = schema_name
            break
        except ValidationError as e:
            # If the error did not happen at the root, return the error and the current schema type (if known)
            error = e
            # If the error did not happen at the root we know the schema type of the JSON
            if len(e.absolute_path) > 0:
                schema_type = schema_name
                break
    return is_valid, error, schema_type
