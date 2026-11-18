"""
Jetlink on this fork: the comma sends camera frames and a phone or a computer
runs the big driving model. The small model stays on the comma and takes back
the drive if the link drops.

The top of this module is the standard library only. Manager imports it to
decide whether jetlinkd should run, and the resident owner imports it for
owner_config(); openpilot and jetlink are imported inside the functions that
need them.
"""
from __future__ import annotations

import functools
import logging
import os

API = 4
OWNER = 'jetlinkd'
MODES = ('off', 'usb', 'ios')

# jetlink.openpilot.status.PHASES. An unknown phase is shown as jetlink wrote it.
_PHASE_TEXT = {
  'off': 'off',
  'unavailable': 'unavailable',
  'preparing': 'preparing the link',
  'connecting': 'connecting',
  'prepared': 'ready',
  'waiting': 'waiting for the host',
  'reconnecting': 'reconnecting',
  'active': 'running the big model',
  'failed': 'failed',
}


def link_on() -> bool:
  """True when the Jetlink setting asks for a host. The param file, not Params:
  manager and modeld both import this module."""
  prefix = os.environ.get('OPENPILOT_PREFIX', '')
  store = os.environ.get('PARAMS_ROOT')
  if store is None:
    store = '/data/params' if os.path.exists('/AGNOS') else os.environ.get('HOME', '') + '/.comma' + prefix + '/params'
  path = os.path.join(store, prefix or 'd', 'JetlinkLink')
  try:
    with open(path, encoding='utf-8') as handle:
      index = int(handle.read().strip() or '0')
  except (OSError, ValueError):
    return False
  return 0 < index < len(MODES)


def _cloudlog():
  try:
    from openpilot.common.swaglog import cloudlog
    return cloudlog
  except Exception:
    return logging.getLogger('jetlink')


class _NoJetlink:
  """Every hook, answered as the link being off. A missing jetlink, or one this
  adapter was not written for, must not take the drive down."""

  def __init__(self, why: str = ''):
    self._why = why

  def should_run(self, *args, **kwargs) -> bool:
    return False

  def status(self):
    return None

  def reason(self) -> str | None:
    return self._why if link_on() else None

  def prepare(self, chestnut: bool) -> bool:
    return False

  def attach(self, model, small, cam_w: int, cam_h: int):
    return model

  def handed_over(self, model) -> bool:
    return False

  def state(self, model) -> str:
    return 'none'

  def runtime(self):
    return None

  def shutdown_step(self, should_shutdown: bool, reason: str = '') -> bool:
    return should_shutdown

  def request_shutdown(self, reason: str = '') -> bool:
    return False

  def shutdown_pending(self) -> bool:
    return False

  def model_state(self, ref: str) -> str | None:
    return None

  def lists_big_models(self) -> bool:
    return False

  def big_catalog(self, selector: int) -> dict | None:
    return None

  def listed_ref(self, ref: str) -> str | None:
    return None

  def should_extend_catalog(self) -> bool:
    return False

  def extend_catalog(self, catalog: dict) -> dict:
    return catalog

  def swap_events(self, tick_s: float):
    return None


def adapter():
  """A new Openpilot for this fork. Built on first use, so importing this module stays light."""
  return _adapter_class()()


def owner_config():
  """What jetlinkd needs, and nothing that pulls in cereal or the logger."""
  return _adapter_class().owner_config()


def _adapter_class():
  from jetlink.openpilot.interface import Keys
  from jetlink.openpilot.stock import Stock

  class Adapter(Stock):
    KEYS = Keys(link='JetlinkLink', offroad='IsOffroad', progress='JetlinkProgress', spec='JetlinkSpec',
                big_model='ModelManager_ActiveBundleChestnut', catalog='ModelManager_ModelsCache_Chestnut',
                charge_phone='JetlinkChargePhone', select='ModelManager_DownloadRef')
    # carControlSP carries MADS, which can be driving while openpilot is paused
    IN_CONTROL_SERVICES = ('carState', 'carControl', 'carControlSP')

    def chestnut_present(self) -> bool:
      # this fork treats a chestnut as the USB product, not a live cable
      from openpilot.selfdrive.modeld.helpers import chestnut_present
      return chestnut_present()

    def model_constants(self):
      from openpilot.sunnypilot.modeld_v2.constants import ModelConstants
      return ModelConstants

    def action_function(self):
      from openpilot.selfdrive.modeld.modeld import get_action_from_model
      return get_action_from_model

    def engaged(self, sm) -> bool:
      return bool(sm['carControl'].enabled or sm['carControlSP'].mads.enabled)

  return Adapter


@functools.cache
def hooks():
  """One facade per process. prepare() and attach() have to be the same one,
  or the join is thrown away and modeld keeps driving the small model."""
  try:
    from jetlink.openpilot.hooks import Hooks
  except ModuleNotFoundError as error:
    return _NoJetlink(f"jetlink failed to import: {error}")
  except Exception as error:
    return _NoJetlink(f"jetlink failed to import: {error}")
  try:
    return Hooks(API, adapter, link_on=link_on, log=_cloudlog)
  except Exception as error:
    return _NoJetlink(f"jetlink is not usable: {error}")


def should_run(*args, **kwargs) -> bool:
  return hooks().should_run(*args, **kwargs)


def status():
  return hooks().status()


def reason() -> str | None:
  return hooks().reason()


def prepare(chestnut: bool) -> bool:
  return hooks().prepare(chestnut)


def attach(model, small, cam_w: int, cam_h: int):
  return hooks().attach(model, small, cam_w, cam_h)


def handed_over(model) -> bool:
  return hooks().handed_over(model)


def shutdown_step(should_shutdown: bool, why: str = '') -> bool:
  return hooks().shutdown_step(should_shutdown, why)


def swap_events(tick_s: float):
  return hooks().swap_events(tick_s)


def lists_big_models() -> bool:
  return hooks().lists_big_models()


def big_catalog(selector: int) -> dict | None:
  return hooks().big_catalog(selector)


def status_line() -> str:
  """One line for the Models panel. None from status() is the parked setup text."""
  shown = status()
  if shown is None:
    return "Off. USB runs the model on a computer. iOS runs it on an iPhone over the comma's USB-C port."
  phase = _PHASE_TEXT.get(getattr(shown, 'phase', ''), getattr(shown, 'phase', '') or 'off')
  progress = getattr(shown, 'progress', None) or {}
  parts = [phase, progress.get('msg') or '', getattr(shown, 'port_state', None) or '']
  return ' '.join(part for part in parts if part)


def main() -> None:
  _adapter_class().main()


if __name__ == '__main__':
  main()
