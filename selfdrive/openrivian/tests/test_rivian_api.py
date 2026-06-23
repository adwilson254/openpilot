"""Tests for the Rivian API client (token handling, headers, login/MFA branches).

Network is never touched: requests.Session.post is monkeypatched.
"""
import json

import pytest

from selfdrive.openrivian.api.rivian_api import RivianAPI


class FakeResp:
    def __init__(self, data, status=200):
        self._data = data
        self.status_code = status
        self.text = json.dumps(data)

    def raise_for_status(self):
        if self.status_code >= 400:
            import requests
            raise requests.exceptions.HTTPError(f"{self.status_code}", response=self)

    def json(self):
        return self._data


def _api_with_tokens(access=None, refresh=None):
    api = RivianAPI()
    if access is not None:
        api.params.put("RivianAccessToken", access)
    if refresh is not None:
        api.params.put("RivianRefreshToken", refresh)
    api._load_tokens()
    return api


def test_load_tokens_new_json_format():
    api = _api_with_tokens(json.dumps({
        "accessToken": "A", "refreshToken": "R", "userSessionToken": "U",
    }))
    assert (api.access_token, api.refresh_token, api.user_session_token) == ("A", "R", "U")
    # user session token takes precedence for the auth header
    assert api.session.headers.get("u-sess") == "U"


def test_load_tokens_legacy_string_fallback():
    api = _api_with_tokens("rawtoken", refresh="rawrefresh")
    assert api.access_token == "rawtoken"
    assert api.refresh_token == "rawrefresh"
    assert api.user_session_token is None
    assert api.session.headers.get("Authorization") == "Bearer rawtoken"


def test_unauthenticated_by_default():
    assert RivianAPI().is_authenticated() is False


def test_login_success_saves_tokens(monkeypatch):
    api = RivianAPI()
    monkeypatch.setattr(api, "create_csrf_token", lambda: True)
    resp = FakeResp({"data": {"login": {
        "__typename": "MobileLoginResponse",
        "accessToken": "A", "refreshToken": "R", "userSessionToken": "U",
    }}})
    monkeypatch.setattr(api.session, "post", lambda *a, **k: resp)

    out = api.login("e@example.com", "pw")
    assert out["status"] == "success"
    assert api.is_authenticated()
    saved = json.loads(api.params.get("RivianAccessToken").decode())
    assert saved["accessToken"] == "A"


def test_login_mfa_required(monkeypatch):
    api = RivianAPI()
    monkeypatch.setattr(api, "create_csrf_token", lambda: True)
    resp = FakeResp({"data": {"login": {
        "__typename": "MobileMFALoginResponse", "otpToken": "OTP",
    }}})
    monkeypatch.setattr(api.session, "post", lambda *a, **k: resp)

    out = api.login("e@example.com", "pw")
    assert out["status"] == "mfa_required"
    assert api.otp_token == "OTP"


def test_login_raises_on_graphql_error(monkeypatch):
    api = RivianAPI()
    monkeypatch.setattr(api, "create_csrf_token", lambda: True)
    monkeypatch.setattr(api.session, "post", lambda *a, **k: FakeResp({"errors": [{"message": "bad"}]}))
    with pytest.raises(Exception):
        api.login("e@example.com", "pw")


def test_login_with_otp_requires_active_session():
    api = RivianAPI()
    with pytest.raises(Exception):
        api.login_with_otp("123456")
