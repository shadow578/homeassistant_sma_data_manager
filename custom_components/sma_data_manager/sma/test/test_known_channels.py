"""Tests for the SMA Data Manager known_channels module."""
from ..known_channels import DEVICE_KIND_GRID, DEVICE_KIND_PV, UNIT_VOLT, UNIT_WATT, get_known_channel


def test_known_channel_normal():
    """
    test if a 'normal' (non-array) known channel is returned correctly

    for 'normal' channels, this is a simple lookup in the known_channels dict
    """

    ch = get_known_channel("Measurement.GridMs.TotW")

    assert ch is not None
    assert ch["device_kind"] == DEVICE_KIND_GRID
    assert ch["unit"] == UNIT_WATT

def test_known_channel_array():
    """
    test if a array known channel is returned correctly

    for array channels, the index brackets are removed and replaced by empty brackets.
    then, the resulting string is used as key in the known_channels dict
    """

    ch = get_known_channel("Measurement.DcMs.Vol[0]")

    assert ch is not None
    assert ch["device_kind"] == DEVICE_KIND_PV
    assert ch["unit"] == UNIT_VOLT

