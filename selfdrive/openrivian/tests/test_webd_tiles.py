"""Tests for the webd map-tile proxy (validation, caching, offline degradation)."""
import io
import os

import pytest

from selfdrive.openrivian import webd


# --------------------------------------------------------------------------- #
# parse_tile_path: the security boundary. Digits-only regex + bounds checks.
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("path,expected", [
    ("/tiles/13/1310/3166.png", (13, 1310, 3166)),
    ("/tiles/3/0/0.png", (3, 0, 0)),
    ("/tiles/19/524287/524287.png", (19, 524287, 524287)),
])
def test_parse_valid_tile_paths(path, expected):
    assert webd.parse_tile_path(path) == expected


@pytest.mark.parametrize("path", [
    "/tiles/2/0/0.png",              # below min zoom
    "/tiles/20/0/0.png",             # above max zoom
    "/tiles/13/8192/0.png",          # x out of range for z=13
    "/tiles/13/0/8192.png",          # y out of range for z=13
    "/tiles/13/-1/0.png",            # negative
    "/tiles/13/1/2.jpg",             # wrong extension
    "/tiles/13/1.png",               # missing coord
    "/tiles/../etc/passwd",          # traversal
    "/tiles/13/..%2F..%2Fetc/1.png", # encoded traversal junk
    "/tilesX/13/1/2.png",
])
def test_parse_rejects_invalid_paths(path):
    assert webd.parse_tile_path(path) is None


def test_tile_cache_path_stays_inside_cache_dir(tmp_path):
    p = webd.tile_cache_path(13, 1310, 3166, cache_dir=str(tmp_path))
    assert os.path.realpath(p).startswith(os.path.realpath(str(tmp_path)))


# --------------------------------------------------------------------------- #
# fetch_tile: cache-first, upstream once, offline -> None (never raises).
# --------------------------------------------------------------------------- #
class _FakeResp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_fetch_tile_caches_after_first_upstream_hit(tmp_path):
    calls = []

    def opener(req, timeout=0):
        calls.append(req.full_url)
        return _FakeResp(b"PNGDATA")

    d = str(tmp_path)
    assert webd.fetch_tile(13, 1, 2, cache_dir=d, opener=opener) == b"PNGDATA"
    # Second call must be served from disk: no new upstream request.
    assert webd.fetch_tile(13, 1, 2, cache_dir=d, opener=opener) == b"PNGDATA"
    assert len(calls) == 1
    assert calls[0] == "https://tile.openstreetmap.org/13/1/2.png"


def test_fetch_tile_sends_identifying_user_agent(tmp_path):
    seen = {}

    def opener(req, timeout=0):
        seen["ua"] = req.get_header("User-agent")
        return _FakeResp(b"X")

    webd.fetch_tile(13, 3, 4, cache_dir=str(tmp_path), opener=opener)
    assert "OpenRivian" in (seen["ua"] or "")


def test_fetch_tile_offline_returns_none(tmp_path):
    def opener(_req, timeout=0):
        raise OSError("no network")

    assert webd.fetch_tile(13, 5, 6, cache_dir=str(tmp_path), opener=opener) is None


def test_fetch_tile_offline_after_cache_still_serves(tmp_path):
    d = str(tmp_path)
    webd.fetch_tile(13, 7, 8, cache_dir=d, opener=lambda r, timeout=0: _FakeResp(b"CACHED"))

    def offline(_req, timeout=0):
        raise OSError("no network")

    assert webd.fetch_tile(13, 7, 8, cache_dir=d, opener=offline) == b"CACHED"


def test_fetch_tile_empty_body_is_none(tmp_path):
    assert webd.fetch_tile(13, 9, 9, cache_dir=str(tmp_path), opener=lambda r, timeout=0: _FakeResp(b"")) is None
