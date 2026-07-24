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
