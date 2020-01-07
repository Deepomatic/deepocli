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


def validate_json(json_data):
    """
    Validate a JSON using the Studio and Vulcan schema
    Returns:
    - is_valid: True if the JSON is valid
    - error: ValidationError raised if not valid
    - schema_type: Studio or Vulcan, or None if both schema raise an error at the root of the JSON
    """
    is_valid, error, schema_type = False, None, None
    schema_dict = {'Studio':STUDIO_JSON_SCHEMA, 'Vulcan':VULCAN_JSON_SCHEMA}
    for schema_name, json_schema in schema_dict.items():
        try:
            validate(instance=json_data, schema=json_schema)
            is_valid = True
            schema_type = schema_name
            break
        except Exception as e:
            # If the error did not happen at the root, return the error and the current schema type
            if len(e.absolute_path) > 0:
                error = e
                schema_type = schema_name
                break
    return is_valid, error, schema_type