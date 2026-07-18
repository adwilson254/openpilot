"""Behavioral tests for the webd route scanner."""
import os

from selfdrive.openrivian import webd


def test_scan_routes_returns_mock_when_path_missing(tmp_path):
    missing = str(tmp_path / "does_not_exist")
    assert webd.scan_routes(missing) == webd.MOCK_ROUTES


def test_scan_routes_lists_dirs_with_sizes_and_dates(tmp_path):
    route = tmp_path / "2024-01-02--03-04-05"
    route.mkdir()
    # ~2 MiB so size_mb floor-divides to 2
    (route / "fcamera.hevc").write_bytes(b"\0" * (2 * 1024 * 1024 + 10))
    # a stray file at the top level must be ignored (only dirs are routes)
    (tmp_path / "loose.txt").write_text("ignored")

    routes = webd.scan_routes(str(tmp_path), io_yield=0)
    assert len(routes) == 1
    r = routes[0]
    assert r["id"] == "2024-01-02--03-04-05"
    assert r["date"] == "2024-01-02"          # split on '--'
    assert r["size_mb"] == 2


def test_scan_routes_empty_dir_returns_empty(tmp_path):
    assert webd.scan_routes(str(tmp_path), io_yield=0) == []


def test_id_without_separator_uses_full_name(tmp_path):
    (tmp_path / "weirdname").mkdir()
    routes = webd.scan_routes(str(tmp_path), io_yield=0)
    assert routes[0]["date"] == "weirdname"


def test_webd_serves_on_expected_port():
    assert webd.PORT == 8081
