from requests import PreparedRequest


def prepare_url(url: str, query: dict):
    """Setup a new url with additional query params."""

    url_req = PreparedRequest()
    url_req.prepare_url(url, query)

    return url_req.url
