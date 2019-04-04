
def transform_json_from_vulcan_to_studio(vulcan_json, name, filename):
    """Transforms a json from the vulcan format to the Studio format."""
    # Initialize variables
    studio_json = {'tags': [], 'images': []}
    unique_tags = set()

    # Loop through all images
    img_studio = {'annotated_regions': []}
    all_predictions = vulcan_json['outputs'][0]['labels']['predicted']
    for prediction in all_predictions:
        # Build studio annotation
        annotation = {
            "tags": [prediction['label_name']],
            "region_type": "Whole",
            "score": prediction['score'],
            "threshold": prediction['threshold']
        }

        # Add bounding box
        if 'roi' in prediction:
            annotation['region_type'] = 'Box'
            annotation['region'] = {
                "xmin": prediction['roi']['bbox']['xmin'],
                "xmax": prediction['roi']['bbox']['xmax'],
                "ymin": prediction['roi']['bbox']['ymin'],
                "ymax": prediction['roi']['bbox']['ymax']
            }

        # Update json
        img_studio['annotated_regions'].append(annotation)

        # Update unique tags
        unique_tags.add(prediction['label_name'])

    # Update json vesta
    studio_json['images'].append(img_studio)
    studio_json['images'][0]['location'] = name
    studio_json['images'][0]['data'] = {'filename': filename}

    # Update unique tags
    studio_json['tags'] = list(unique_tags)

    return studio_json
