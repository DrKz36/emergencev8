from types import SimpleNamespace

from backend.shared.dependencies import _extract_token_from_request


DUMMY_TOKEN = "aaa.bbb.ccc"


def _make_request(*, headers=None, cookies=None, query=None):
    return SimpleNamespace(
        headers=headers or {},
        cookies=cookies or {},
        query_params=query or {},
    )


def test_extract_token_from_authorization_header():
    request = _make_request(headers={"Authorization": f"Bearer {DUMMY_TOKEN}"})

    extracted = _extract_token_from_request(request)

    assert extracted == DUMMY_TOKEN


def test_extract_token_from_cookie_fallback():
    request = _make_request(cookies={"id_token": DUMMY_TOKEN})

    extracted = _extract_token_from_request(request)

    assert extracted == DUMMY_TOKEN


def test_extract_token_from_query_params_fallback():
    request = _make_request(query={"token": f"Bearer {DUMMY_TOKEN}"})

    extracted = _extract_token_from_request(request)

    assert extracted == DUMMY_TOKEN


def test_extract_token_returns_empty_string_when_missing():
    request = _make_request()

    extracted = _extract_token_from_request(request)

    assert extracted == ""
