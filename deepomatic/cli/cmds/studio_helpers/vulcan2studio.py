
def transform_json_from_vulcan_to_studio(vulcan_json):
    """Transforms a json from the vulcan format to the studio format."""
    # Initialize variables
    studio_json = {'tags': [], 'images': []}
    unique_tags = set()

    # Transform vulcan json to a list of vulcan json if needed
    if isinstance(vulcan_json, dict):
        vulcan_json = [vulcan_json]

    # Loop through all vulcan images
    for vulcan_image in vulcan_json:
        # Initialize studio images
        studio_image = {'annotated_regions': [], 'location': vulcan_image.get('location', '')}
        if 'data' in vulcan_image:
            studio_image['data'] = vulcan_image['data']

        # Loop through all vulcan predictions
        all_predictions = vulcan_image['outputs'][0]['labels']['predicted'] + vulcan_image['outputs'][0]['labels']['discarded']
        for prediction in all_predictions:
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


def transform_json_from_studio_to_vulcan(studio_json):
    """Transforms a json from the studio format to the vulcan format."""
    # Initialize variables
    vulcan_json = []

    # Loop through all studio images
    for studio_image in studio_json['images']:
        # Initialize vulcan prediction
        vulcan_pred = {'outputs': [{'labels': {'discarded': [], 'predicted': []}}]}
        predicted = []
        discarded = []
        for metadata in ['location', 'data']:
            if metadata in studio_image:
                vulcan_pred[metadata] = studio_image[metadata]

        # Loop through all studio predictions
        for studio_pred in studio_image['annotated_regions']:
            # Build vulcan annotation
            annotation = {
                'label_name': studio_pred['tags'][0],
                'score': studio_pred['score'],
                'threshold': studio_pred['threshold']
            }

            # Add bounding box if needed
            if studio_pred['region_type'] == 'Box':
                annotation['roi'] = {
                    'bbox': {
                        'xmin': studio_pred['region']['xmin'],
                        'xmax': studio_pred['region']['xmax'],
                        'ymin': studio_pred['region']['ymin'],
                        'ymax': studio_pred['region']['ymax']
                    }
                }

            # Update json
            if annotation['score'] >= annotation['threshold']:
                predicted.append(annotation)
            else:
                discarded.append(annotation)

        # Sort by prediction score of descending order
        predicted = sorted(predicted, key=lambda k: k['score'], reverse=True)
        discarded = sorted(discarded, key=lambda k: k['score'], reverse=True)
        vulcan_pred['outputs'][0]['labels']['predicted'] = predicted
        vulcan_pred['outputs'][0]['labels']['discarded'] = discarded

        # Update vulcan json
        vulcan_json.append(vulcan_pred)

    return vulcan_json
