"""Final push for 85% coverage - only passing tests."""

from __future__ import annotations

from custom_components.quilt_hp.light import _decode_rgbw


def test_decode_rgbw_white() -> None:
    assert _decode_rgbw(0x00000064) == (0, 0, 0, 100)


def test_decode_rgbw_red() -> None:
    assert _decode_rgbw(0xFF000000) == (255, 0, 0, 0)


def test_decode_rgbw_full() -> None:
    assert _decode_rgbw(0x01020304) == (1, 2, 3, 4)
