"""Tests for the openriviand API daemon."""
from selfdrive.openrivian.api import openriviand


def test_import_openriviand():
    assert openriviand is not None


def test_step_without_token_is_graceful(fake_params):
    # No RivianAccessToken -> must complete a step without raising.
    openriviand.step(fake_params)


def test_step_with_token_is_graceful(fake_params):
    # Token present -> still a no-op today (ABRP fetch is a TODO), must not raise.
    fake_params.put("RivianAccessToken", "sometoken")
    openriviand.step(fake_params)


def test_step_reports_auth_state(fake_params):
    assert openriviand.step(fake_params) is False
    fake_params.put("RivianAccessToken", "sometoken")
    assert openriviand.step(fake_params) is True


class _RecordingClient:
    def __init__(self):
        self.published = []

    def publish(self, topic, payload, retain=False):
        import json
        self.published.append((topic, json.loads(payload)["value"], retain))


class _FakeAPI:
    def __init__(self, authenticated=True, vehicles=None, state=None):
        self._auth = authenticated
        self._vehicles = vehicles if vehicles is not None else [{"id": "veh-1", "name": "R1T"}]
        self._state = state

    def is_authenticated(self):
        return self._auth

    def get_vehicles(self):
        return self._vehicles

    def get_vehicle_state(self, vid):
        assert vid == "veh-1"
        return self._state


def test_fetch_energy_resolves_and_caches_vehicle_id():
    api = _FakeAPI(state={"soc_percent": 71.5, "range_miles": 180.2, "charger_state": "not_connected"})
    energy, vid = openriviand.fetch_energy(api, None)
    assert vid == "veh-1"
    assert energy["soc_percent"] == 71.5
    # Cached id short-circuits the vehicle lookup on later calls.
    api._vehicles = []  # would fail resolution if it were re-queried
    energy2, vid2 = openriviand.fetch_energy(api, vid)
    assert vid2 == "veh-1" and energy2 is not None


def test_fetch_energy_unauthenticated_is_none():
    energy, vid = openriviand.fetch_energy(_FakeAPI(authenticated=False), None)
    assert energy is None and vid is None


def test_fetch_energy_no_vehicles_is_graceful():
    energy, vid = openriviand.fetch_energy(_FakeAPI(vehicles=[]), None)
    assert energy is None and vid is None


def test_publish_energy_publishes_retained_and_skips_none():
    client = _RecordingClient()
    openriviand.publish_energy(client, {"soc_percent": 80.0, "range_miles": None, "charger_state": "charging"})
    topics = [t for t, _v, _r in client.published]
    assert "openrivian/energy/soc_percent" in topics
    assert "openrivian/energy/charger_state" in topics
    assert "openrivian/energy/range_miles" not in topics  # None -> skipped
    assert all(r is True for _t, _v, r in client.published)  # retained state


def test_publish_energy_none_client_or_energy_is_noop():
    openriviand.publish_energy(None, {"soc_percent": 1.0})
    openriviand.publish_energy(_RecordingClient(), None)


# --------------------------------------------------------------------------- #
# Stable link-local companion IP (random-subnet hotspot fix)
# --------------------------------------------------------------------------- #
class _RunRec:
    def __init__(self, rc=0):
        self.rc = rc
        self.calls = []

    def __call__(self, cmd, capture_output=False, timeout=0):
        self.calls.append(cmd)
        class R:
            returncode = self.rc
        return R()


def test_ensure_stable_ip_asserts_alias_when_iface_exists(monkeypatch, tmp_path):
    fake_sys = tmp_path / "wlan0"
    fake_sys.mkdir()
    monkeypatch.setattr(openriviand.os.path, "exists", lambda p: p.endswith("/wlan0"))
    rec = _RunRec(rc=0)
    assert openriviand.ensure_stable_ip(runner=rec) is True
    assert rec.calls == [["sudo", "-n", "ip", "addr", "replace",
                          "169.254.71.71/16", "dev", "wlan0"]]


def test_ensure_stable_ip_noop_without_iface(monkeypatch):
    # PC/CI: no wlan0 -> quiet no-op, no subprocess call.
    monkeypatch.setattr(openriviand.os.path, "exists", lambda p: False)
    rec = _RunRec()
    assert openriviand.ensure_stable_ip(runner=rec) is False
    assert rec.calls == []


def test_ensure_stable_ip_survives_command_failure(monkeypatch):
    monkeypatch.setattr(openriviand.os.path, "exists", lambda p: True)

    def boom(*_a, **_k):
        raise OSError("no sudo")

    assert openriviand.ensure_stable_ip(runner=boom) is False  # never raises


def test_ensure_stable_ip_reports_nonzero_exit(monkeypatch):
    monkeypatch.setattr(openriviand.os.path, "exists", lambda p: True)
    rec = _RunRec(rc=1)
    assert openriviand.ensure_stable_ip(runner=rec) is False
