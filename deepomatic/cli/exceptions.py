class DeepoException(Exception):
    pass


class DeepoRPCUnavailableError(DeepoException):
    pass


class DeepoRPCRecognitionError(DeepoException):
    pass


class DeepoCLICredentialsError(DeepoException):
    pass
