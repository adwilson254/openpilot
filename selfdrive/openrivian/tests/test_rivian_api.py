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


# --------------------------------------------------------------------------- #
# Timeouts: every network call must bound its wait (the mici panel calls this
# client synchronously on the UI render thread).
# --------------------------------------------------------------------------- #
def test_all_posts_carry_a_timeout(monkeypatch):
    api = RivianAPI()
    seen = []

    def rec_post(url, json=None, timeout=None, **_k):
        seen.append(timeout)
        return FakeResp({"data": {"createCsrfToken": {"csrfToken": "c", "appSessionToken": "a"}}})

    monkeypatch.setattr(api.session, "post", rec_post)
    api.create_csrf_token()
    assert seen and all(t is not None for t in seen)


def test_source_has_no_timeoutless_posts():
    # Static guard: any future session.post added without a timeout fails here.
    import inspect
    import re
    from selfdrive.openrivian.api import rivian_api
    src = inspect.getsource(rivian_api)
    for call in re.findall(r"session\.post\([^)]*\)", src):
        assert "timeout" in call, f"session.post without timeout: {call}"


# --------------------------------------------------------------------------- #
# Vehicle state (energy) accessors
# --------------------------------------------------------------------------- #
def _vehicle_state_resp(soc=71.5, dte_km=290.0, charger="not_connected"):
    return FakeResp({"data": {"vehicleState": {
        "__typename": "VehicleState",
        "batteryLevel": {"value": soc},
        "distanceToEmpty": {"value": dte_km},
        "chargerState": {"value": charger},
    }}})


def test_get_vehicle_state_parses_timestamped_fields(monkeypatch):
    api = _api_with_tokens("tok")
    monkeypatch.setattr(api.session, "post", lambda *a, **k: _vehicle_state_resp())
    out = api.get_vehicle_state("veh-1")
    assert out["soc_percent"] == 71.5
    assert out["range_miles"] == round(290.0 * 0.621371, 1)
    assert out["charger_state"] == "not_connected"


def test_get_vehicle_state_accepts_raw_scalars(monkeypatch):
    api = _api_with_tokens("tok")
    resp = FakeResp({"data": {"vehicleState": {
        "batteryLevel": 55.0, "distanceToEmpty": 100.0, "chargerState": "charging",
    }}})
    monkeypatch.setattr(api.session, "post", lambda *a, **k: resp)
    out = api.get_vehicle_state("veh-1")
    assert out["soc_percent"] == 55.0
    assert out["charger_state"] == "charging"


def test_get_vehicle_state_defensive_on_errors(monkeypatch):
    api = _api_with_tokens("tok")
    monkeypatch.setattr(api.session, "post", lambda *a, **k: FakeResp({"errors": [{"message": "nope"}]}))
    assert api.get_vehicle_state("veh-1") is None
    # unauthenticated / missing id never hit the network
    assert RivianAPI().get_vehicle_state("veh-1") is None
    assert api.get_vehicle_state(None) is None


def test_get_vehicles_defensive(monkeypatch):
    api = _api_with_tokens("tok")
    resp = FakeResp({"data": {"currentUser": {"vehicles": [
        {"id": "veh-1", "name": "R1T", "vin": "V"}, {"name": "no-id"},
    ]}}})
    monkeypatch.setattr(api.session, "post", lambda *a, **k: resp)
    out = api.get_vehicles()
    assert out == [{"id": "veh-1", "name": "R1T", "vin": "V"}]
    monkeypatch.setattr(api.session, "post", lambda *a, **k: FakeResp({"errors": [{}]}))
    assert api.get_vehicles() == []
    assert RivianAPI().get_vehicles() == []
