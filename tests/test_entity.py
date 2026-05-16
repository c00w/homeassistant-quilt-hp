"""Tests for the entity module."""

from __future__ import annotations

from custom_components.quilt_hp.entity import (
    QuiltEntity,
    _clean,
    controller_device_info,
    ctrl_remote_sensor_device_info,
    idu_device_info,
    location_device_info,
    odu_device_info,
    remote_sensor_device_info,
)

from .conftest import (
    make_controller,
    make_ctrl_remote_sensor,
    make_idu,
    make_location,
    make_mock_coordinator,
    make_odu,
    make_remote_sensor,
    make_snapshot,
    make_space,
)


async def test_clean_none(hass) -> None:
    """Test _clean with None."""
    assert _clean(None) is None


async def test_clean_sentinel_values(hass) -> None:
    """Test _clean with sentinel values."""
    assert _clean("N/A") is None
    assert _clean("n/a") is None
    assert _clean("NA") is None
    assert _clean("") is None


async def test_clean_valid_string(hass) -> None:
    """Test _clean with valid string."""
    assert _clean("valid") == "valid"
    assert _clean("123") == "123"


async def test_quilt_entity_init(hass) -> None:
    """Test QuiltEntity initialization."""
    snapshot = make_snapshot()
    coordinator = make_mock_coordinator(hass, snapshot)

    entity = QuiltEntity(coordinator)
    assert entity.coordinator == coordinator
    assert entity._attr_has_entity_name is True


async def test_quilt_entity_refresh_when_not_streaming(hass) -> None:
    """Test refresh request when not streaming."""
    snapshot = make_snapshot()
    coordinator = make_mock_coordinator(hass, snapshot)
    coordinator.is_streaming = False

    entity = QuiltEntity(coordinator)
    await entity._async_refresh_if_not_streaming()

    coordinator.async_request_refresh.assert_awaited_once()


async def test_quilt_entity_no_refresh_when_streaming(hass) -> None:
    """Test no refresh when streaming is active."""
    snapshot = make_snapshot()
    coordinator = make_mock_coordinator(hass, snapshot)
    coordinator.is_streaming = True

    entity = QuiltEntity(coordinator)
    await entity._async_refresh_if_not_streaming()

    coordinator.async_request_refresh.assert_not_awaited()


async def test_idu_device_info_with_name(hass) -> None:
    """Test IDU device info with configured name."""
    idu = make_idu()
    idu.settings.name = "Master Bedroom IDU"
    space = make_space(name="Master Bedroom")

    info = idu_device_info(idu, space)

    assert info["name"] == "Master Bedroom IDU"
    assert info["manufacturer"] == "Quilt"
    assert info["model"] == "Indoor Unit"
    assert info["suggested_area"] == "Master Bedroom"
    assert ("quilt_hp", f"i_{idu.id}") in info["identifiers"]


async def test_idu_device_info_without_name(hass) -> None:
    """Test IDU device info without configured name."""
    idu = make_idu()
    idu.settings.name = ""
    space = make_space(name="Living Room")

    info = idu_device_info(idu, space)

    assert info["name"] == "Living Room Indoor Unit"
    assert info["suggested_area"] == "Living Room"


async def test_idu_device_info_no_space(hass) -> None:
    """Test IDU device info without space."""
    idu = make_idu()
    idu.settings.name = None

    info = idu_device_info(idu, None)

    assert info["name"].startswith("Indoor Unit")
    assert "suggested_area" not in info


async def test_odu_device_info(hass) -> None:
    """Test ODU device info."""
    odu = make_odu()
    odu.model_sku = "QHP-36K"
    odu.serial_number = "SN123456"
    odu.firmware_version = "1.2.3"
    idu = make_idu()

    info = odu_device_info(odu, idu)

    assert info["manufacturer"] == "Quilt"
    assert "QHP-36K" in info["model"]
    assert info["serial_number"] == "SN123456"
    assert info["sw_version"] == "1.2.3"
    assert ("quilt_hp", f"u_{odu.id}") in info["identifiers"]
    assert info["via_device"] == ("quilt_hp", f"i_{idu.id}")


async def test_odu_device_info_no_idu(hass) -> None:
    """Test ODU device info without IDU."""
    odu = make_odu()

    info = odu_device_info(odu, None)

    assert "via_device" not in info


async def test_controller_device_info(hass) -> None:
    """Test controller device info."""
    ctrl = make_controller()
    ctrl.name = "Kitchen Dial"
    ctrl.model_sku = "DIAL-V2"
    ctrl.serial_number = "CTRL-123"
    ctrl.firmware_version = "2.0.1"
    idu = make_idu()

    info = controller_device_info(ctrl, idu)

    assert info["name"] == "Kitchen Dial"
    assert info["manufacturer"] == "Quilt"
    assert info["model"] == "DIAL-V2"
    assert info["serial_number"] == "CTRL-123"
    assert info["sw_version"] == "2.0.1"
    assert ("quilt_hp", f"c_{ctrl.id}") in info["identifiers"]
    assert info["via_device"] == ("quilt_hp", f"i_{idu.id}")


async def test_controller_device_info_no_idu(hass) -> None:
    """Test controller device info without IDU."""
    ctrl = make_controller()

    info = controller_device_info(ctrl, None)

    assert "via_device" not in info


async def test_remote_sensor_device_info(hass) -> None:
    """Test remote sensor device info."""
    rs = make_remote_sensor()
    idu = make_idu()

    info = remote_sensor_device_info(rs, idu)

    assert info["manufacturer"] == "Quilt"
    assert info["model"] == "Remote Sensor"
    assert ("quilt_hp", f"rs_{rs.id}") in info["identifiers"]
    assert info["via_device"] == ("quilt_hp", f"i_{idu.id}")


async def test_controller_remote_sensor_device_info(hass) -> None:
    """Test controller remote sensor device info."""
    crs = make_ctrl_remote_sensor()
    ctrl = make_controller()

    info = ctrl_remote_sensor_device_info(crs, ctrl)

    assert info["manufacturer"] == "Quilt"
    assert "Zone Sensor" in info["model"]
    assert ("quilt_hp", f"crs_{crs.id}") in info["identifiers"]
    assert info["via_device"] == ("quilt_hp", f"c_{ctrl.id}")


async def test_controller_remote_sensor_device_info_with_name(hass) -> None:
    """Test controller remote sensor device info with controller name."""
    crs = make_ctrl_remote_sensor()
    ctrl = make_controller()
    ctrl.name = "Kitchen Dial"

    info = ctrl_remote_sensor_device_info(crs, ctrl)

    assert "Kitchen Dial" in info["name"]


async def test_location_device_info(hass) -> None:
    """Test location device info."""
    loc = make_location(name="My Home")

    info = location_device_info(loc)

    assert info["name"] == "My Home"
    assert info["manufacturer"] == "Quilt"
    assert "System" in info["model"]
    assert ("quilt_hp", f"loc_{loc.id}") in info["identifiers"]
