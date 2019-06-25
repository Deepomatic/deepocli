class DeepoException(Exception):
    pass


class DeepoRPCUnavailableError(DeepoException):
    pass


class DeepoRPCRecognitionError(DeepoException):
    pass


class DeepoCLICredentialsError(DeepoException):
    pass


class DeepoWorkflowError(DeepoException):
    pass


class DeepoUnknownOutputError(DeepoException):
    pass


class DeepoSaveJsonToFileError(DeepoException):
    pass


class DeepoFPSError(DeepoException):
    pass


class DeepoVideoOpenError(DeepoException):
    pass


class DeepoInputError(DeepoException):
    pass


class DeepoPredictionJsonError(DeepoException):
    pass
