import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "jetlink_repo"))

import pytest

from openpilot.sunnypilot import jetlink_adapter
from jetlink.openpilot.testing import check_adapter, check_fallback, check_seam

HEAVY = ("openpilot.common.params", "openpilot.common.swaglog", "openpilot.cereal")
MODELD = (
  ROOT / "openpilot/selfdrive/modeld/modeld.py",
  ROOT / "openpilot/sunnypilot/modeld_v2/modeld.py",
)


@pytest.fixture(autouse=True)
def isolated_params(tmp_path, monkeypatch):
  monkeypatch.setenv("PARAMS_ROOT", str(tmp_path))
  store = tmp_path / "d"
  store.mkdir()
  (store / "JetlinkLink").write_text("0")


def test_link_off_until_a_mode_is_chosen(tmp_path):
  assert jetlink_adapter.link_on() is False
  (tmp_path / "d" / "JetlinkLink").write_text("2")
  assert jetlink_adapter.link_on() is True
  (tmp_path / "d" / "JetlinkLink").write_text("0")
  assert jetlink_adapter.link_on() is False


def test_adapter_matches_jetlink():
  assert check_adapter(jetlink_adapter, heavy=HEAVY) == []


def test_modeld_seams():
  for path in MODELD:
    assert check_seam(path) == []


def test_missing_jetlink_answers_as_off():
  assert check_fallback(jetlink_adapter._NoJetlink("jetlink is missing"), link_on=jetlink_adapter.link_on) == []
