import requests.exceptions
import typesense.exceptions


class TypesenseUnavailable(Exception):
    """The search backend could not serve a request."""


TYPESENSE_UNAVAILABLE_MESSAGE = "Recording search is temporarily unavailable. Please try again later."


def search(client, collection, parameters):
    try:
        return client.collections[collection].documents.search(parameters)
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout,
            typesense.exceptions.Timeout, typesense.exceptions.ServerError,
            typesense.exceptions.ServiceUnavailable, typesense.exceptions.HTTPStatus0Error) as exc:
        raise TypesenseUnavailable(TYPESENSE_UNAVAILABLE_MESSAGE) from exc
    except typesense.exceptions.TypesenseClientError as exc:
        # The SDK uses its base exception when all nodes are unhealthy.
        if type(exc) is typesense.exceptions.TypesenseClientError:
            raise TypesenseUnavailable(TYPESENSE_UNAVAILABLE_MESSAGE) from exc
        # Preserve specific errors such as malformed queries and invalid credentials.
        raise
