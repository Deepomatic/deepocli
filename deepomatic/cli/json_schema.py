from jsonschema import validate, ValidationError


class JSONSchemaType:
    STUDIO_HEADER = 'Studio-header'
    STUDIO_INPUT = 'Studio-input'
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
    CONCEPT_SCHEMA = {
        "type": "object",
        "required": ["name"],
        "additionalProperties": False,
        "properties": {
            "name": {
                "type": "string"
            },
            "bool": {
                "type": "boolean"
            }
        }
    }

    HEADER_SCHEMA = {
        "type": "object",
        "required": [
            "name",
            "splits",
            "views"
        ],
        "additionalProperties": False,
        "properties": {
            "name": {
                "type": "string"
            },
            "splits": {
                "type": "array",
                "items": [
                    {
                        "type": "string",
                        "enum": ["train", "val"]
                    },
                    {
                        "type": "string",
                        "enum": ["train", "val"]
                    }
                ]
            },
            "views": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": [
                        "concepts",
                        "type",
                        "name",
                        "conditions"
                    ],
                    "additionalProperties": False,
                    "properties": {
                        "name": {
                            "type": "string"
                        },
                        "type": {
                            "type": "string"
                        },
                        "concepts": {
                            "type": "array",
                            "items": CONCEPT_SCHEMA
                        },
                        "conditions": {
                            "type": "array"
                        },
                        "id": {
                            "type": ["number", "null"]
                        }
                    }
                }
            }
        }
    }

    ANNOTATION_SCHEMA = {
        "type": "array",
        "items": {
            "type": "object",
            "required": ["concepts", "region"],
            "additionalProperties": False,
            "properties": {
                "concepts": {
                    "type": "array",
                    "objects": CONCEPT_SCHEMA
                },
                "region": {
                    "type": "object",
                    "required": ["bbox"],
                    "additionalProperties": False,
                    "properties": {
                        "bbox": {
                            "type": "object",
                            "required": ["xmin", "xmax", "ymin", "ymax"],
                            "additionalProperties": False,
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

    IMAGE_SCHEMA = {
        "type": "object",
        "required": [
            "data"
        ],
        "additionalProperties": False,
        "properties": {
            "id": {
                "type": ["number", "null"]
            },
            "data": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["file"],
                    "additionalProperties": False,
                    "properties": {
                        "file": {
                            "type": "string"
                        }
                    }
                }
            },
            "metadata": {
                "type": "string"
            },
            "annotations": ANNOTATION_SCHEMA,
            "splits": {
                "type": "array",
                "items": {
                    "anyOf": [
                        {"required": ["train"]},
                        {"required": ["val"]}
                    ]
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
    schema_dict = {JSONSchemaType.STUDIO_HEADER: JSONSchemaType.HEADER_SCHEMA,
                   JSONSchemaType.STUDIO_INPUT: JSONSchemaType.IMAGE_SCHEMA,
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
