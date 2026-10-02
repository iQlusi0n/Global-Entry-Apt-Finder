import base64

import pytest

from ge_apt_finder.notify import Notifier, NotifierConfigError


def test_from_env_requires_url(monkeypatch):
    monkeypatch.delenv("NTFY_URL", raising=False)
    with pytest.raises(NotifierConfigError):
        Notifier.from_env()


def test_auth_header_prefers_token_over_basic():
    n = Notifier(url="https://ntfy.sh/t", user="u", password="p", token="tok")
    assert n._auth_header() == "Bearer tok"


def test_auth_header_basic_encodes_credentials():
    n = Notifier(url="https://ntfy.sh/t", user="u", password="p")
    assert n._auth_header() == "Basic " + base64.b64encode(b"u:p").decode()


def test_auth_header_none_when_anonymous():
    assert Notifier(url="https://ntfy.sh/t")._auth_header() is None
