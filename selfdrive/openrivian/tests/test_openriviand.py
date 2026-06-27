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
