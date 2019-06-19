
def transform_json_from_vulcan_to_studio(vulcan_json):
    """Transforms a json from the vulcan format to the Studio format."""
    # Initialize variables
    studio_json = {'tags': [], 'images': []}
    unique_tags = set()

    # Transform vulcan json to a list of vulcan json if needed
    if isinstance(vulcan_json, dict):
        vulcan_json = [vulcan_json]

    # Loop through all vulcan images
    for vulcan_image in vulcan_json:
        # Initialize studio images
        studio_image = {'annotated_regions': []}

        # Loop through all vulcan predictions
        for prediction in vulcan_image['outputs'][0]['labels']['predicted']:
            # Build studio annotation in case of classification or tagging
            annotation = {
                "tags": [prediction['label_name']],
                "region_type": "Whole",
                "score": prediction['score'],
                "threshold": prediction['threshold']
            }

            # Add bounding box if needed
            if 'roi' in prediction:
                annotation['region_type'] = 'Box'
                annotation['region'] = {
                    "xmin": prediction['roi']['bbox']['xmin'],
                    "xmax": prediction['roi']['bbox']['xmax'],
                    "ymin": prediction['roi']['bbox']['ymin'],
                    "ymax": prediction['roi']['bbox']['ymax']
                }

            # Update json and unique tags
            studio_image['annotated_regions'].append(annotation)
            unique_tags.add(prediction['label_name'])

        # Update studio json
        studio_json['images'].append(studio_image)

    # Update final unique tags
    studio_json['tags'] = list(unique_tags)

    return studio_json
