class DeepoCLIException(Exception):
    pass


class DeepoRPCUnavailableError(DeepoCLIException):
    pass


class DeepoRPCRecognitionError(DeepoCLIException):
    pass


class DeepoCLICredentialsError(DeepoCLIException):
    pass


class DeepoWorkflowError(DeepoCLIException):
    pass


class DeepoUnknownOutputError(DeepoCLIException):
    pass


class DeepoSaveJsonToFileError(DeepoCLIException):
    pass


class DeepoOpenJsonError(DeepoCLIException):
    pass


class DeepoFPSError(DeepoCLIException):
    pass


class DeepoVideoOpenError(DeepoCLIException):
    pass


class DeepoInputError(DeepoCLIException):
    pass


class DeepoPredictionJsonError(DeepoCLIException):
    pass


class DeepoUploadJsonError(DeepoCLIException):
    pass


# Inference errors


class InferenceError(DeepoCLIException):
    def __init__(self, error):
        super(InferenceError, self).__init__(str(error))
        self.error = error


class SendInferenceError(InferenceError):
    pass


class ResultInferenceError(InferenceError):
    pass


class ResultInferenceTimeout(ResultInferenceError):
    def __init__(self, timeout=None):
        self.timeout = timeout
        error = 'timeout reached'
        if timeout is not None:
            error += ' after {}'.format(timeout)
        super(ResultInferenceTimeout, self).__init__(error)
