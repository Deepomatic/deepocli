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
