"""
Implementation of exceptions

..currentmodule:: garlic.exc
"""
from asks.response_objects import Response


class HTTPError(Exception):
    """
    Base exception for all HTTP related errors.

    :param response: Response object accompanying the http error.
    """
    def __init__(self, response: Response):
        self.response = response


class BadRequest(HTTPError):
    """
    400 Bad Request: The request for a known resource could not be processed
    because of bad syntax.
    """
    pass


class NotFound(HTTPError):
    """
    404 Not Available: The request could not be processed because the
    requested resource could not be found.
    """
    pass


class InternalServerError(HTTPError):
    """
    500 Internal Server Error: There is an unspecific problem with the server
    which the service operator may not yet be aware of.
    """
    pass


class ServiceUnavailable(HTTPError):
    """
    503 Service Unavailable: The server is temporarily down for maintenance,
    or there is a temporary problem with the server that the service operator
    is already aware of.
    """
    pass
