import os


class AbstractWorkflow(object):
    class AbstractInferResult(object):
        def __init__(self, threshold):
            self.threshold = threshold

        def filter_by_threshold(self, predictions):
            if self.threshold is not None:
                # Keep only predictions higher than threshold
                for output in predictions['outputs']:
                    labels = output['labels']
                    labels['predicted'] = [prediction 
                        for prediction in labels['predicted']+labels['discarded']
                            if prediction['score'] >= self.threshold]
                    labels['discarded'] = [prediction 
                            for prediction in labels['predicted']+labels['discarded']
                                if prediction['score'] < self.threshold]
            return predictions

        def get_predictions(self):
            raise NotImplementedError()

    def new_client(self):
        return None

    def close_client(self, client):
        pass

    def close(self):
        raise NotImplementedError()

    def infer(self, encoded_image_bytes, push_client):
        """Should return a subclass of AbstractInferResult"""
        raise NotImplementedError()