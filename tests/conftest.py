"""Shared test fixtures for the Quilt Heat Pump integration tests."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

from homeassistant.core import HomeAssistant
from quilt_hp.models.enums import (
    FanSpeed,
    HVACMode,
    HVACState,
    LedAnimation,
    LightState,
    LouverMode,
    OccupancyMode,
    SafetyHeatingMode,
)
from quilt_hp.models.indoor_unit import (
    IndoorUnit,
    IndoorUnitControls,
    IndoorUnitSettings,
    IndoorUnitState,
)
from quilt_hp.models.outdoor_unit import OutdoorUnit, OutdoorUnitPerformanceData
from quilt_hp.models.space import Space, SpaceControls, SpaceSettings, SpaceState

# ── Model helpers ─────────────────────────────────────────────────────────────


def make_space(
    space_id: str = "space-001",
    system_id: str = "sys-001",
    name: str = "Living Room",
    parent_space_id: str = "root-001",
    hvac_mode: HVACMode = HVACMode.HEAT,
    hvac_state: HVACState = HVACState.HEAT,
    ambient_temp_c: float = 21.0,
    heat_setpoint_c: float = 22.0,
    cool_setpoint_c: float = 25.0,
) -> Space:
    return Space(
        id=space_id,
        system_id=system_id,
        name=name,
        parent_space_id=parent_space_id,
        settings=SpaceSettings(
            name=name,
            timezone="America/Los_Angeles",
            occupancy_mode=OccupancyMode.DISABLED,
            occupied_timeout_s=180,
            unoccupied_timeout_s=1200,
            safety_heating=SafetyHeatingMode.ENABLED,
        ),
        controls=SpaceControls(
            hvac_mode=hvac_mode,
            temperature_setpoint_c=heat_setpoint_c,
            cooling_setpoint_c=cool_setpoint_c,
            heating_setpoint_c=heat_setpoint_c,
            comfort_setting_id="cs-001",
            comfort_setting_override=0,
        ),
        state=SpaceState(
            ambient_temperature_c=ambient_temp_c,
            hvac_state=hvac_state,
            setpoint_c=heat_setpoint_c,
            comfort_setting_id="cs-001",
        ),
    )


def make_idu(
    idu_id: str = "idu-001",
    system_id: str = "sys-001",
    space_id: str = "space-001",
    outdoor_unit_id: str | None = "odu-001",
    online: bool = True,
    fan_speed: FanSpeed = FanSpeed.AUTO,
    louver_mode: LouverMode = LouverMode.AUTO,
    louver_fixed_position: float = 0.0,
    led_on: bool = True,
    led_brightness: float = 0.8,
    led_color_code: int = 0xFF460064,
) -> IndoorUnit:
    return IndoorUnit(
        id=idu_id,
        system_id=system_id,
        space_id=space_id,
        outdoor_unit_id=outdoor_unit_id,
        hardware_id="hw-001",
        qsm_id=None,
        settings=IndoorUnitSettings(
            name="Living Room IDU",
            description="",
            light_brightness_default_percent=0.8,
            presence_fence_left_m=0.0,
            presence_fence_right_m=0.0,
            presence_fence_forward_m=0.0,
            radar_sensor_distance_from_floor_m=2.4,
        ),
        controls=IndoorUnitControls(
            fan_speed=fan_speed,
            louver_mode=louver_mode,
            louver_fixed_position=louver_fixed_position,
            led_color_code=led_color_code if led_on else 0,
            led_brightness=led_brightness,
            led_animation=LedAnimation.NONE,
            led_state=LightState.ON if led_on else LightState.OFF,
        ),
        state=IndoorUnitState(
            hvac_mode=HVACMode.HEAT,
            hvac_state=HVACState.HEAT,
            ambient_temperature_c=21.5,
            ambient_humidity_percent=45.0,
            fan_speed_rpm=800.0,
            fan_speed_setpoint_rpm=820.0,
            presence_detection_level=0.1,
            updated_at=datetime.now(tz=UTC) if online else None,
        ),
        hvac_inputs=None,
        conditions=None,
        performance_data=None,
        performance_metrics=None,
        presence=None,
        occupancy=None,
    )


def make_odu(
    odu_id: str = "odu-001",
    system_id: str = "sys-001",
    space_id: str = "space-001",
) -> OutdoorUnit:
    return OutdoorUnit(
        id=odu_id,
        system_id=system_id,
        space_id=space_id,
        hvac_state=2,
        model_sku="QHP-1234",
        serial_number="SN-12345",
        firmware_version="1.2.3",
        firmware_update_info_id=None,
        performance_data=OutdoorUnitPerformanceData(
            measurement_interval_s=5.0,
            energy_measurement_j=1000.0,
            compressor_frequency_hz=55.0,
            ambient_temperature_c=5.0,
            coil_temperature_c=10.0,
            exhaust_temperature_c=35.0,
            high_pressure_kpa=2500.0,
            low_pressure_kpa=800.0,
        ),
    )


def make_snapshot(
    spaces=None,
    indoor_units=None,
    outdoor_units=None,
) -> MagicMock:
    """Build a minimal SystemSnapshot mock."""
    snapshot = MagicMock()
    snapshot.spaces = spaces or [make_space()]
    snapshot.indoor_units = indoor_units or [make_idu()]
    snapshot.outdoor_units = outdoor_units or [make_odu()]
    snapshot.stream_topics.return_value = ["topic-1"]
    snapshot.apply_space.side_effect = lambda s: s
    snapshot.apply_indoor_unit.side_effect = lambda u: u
    snapshot.apply_outdoor_unit.side_effect = lambda u: u
    return snapshot


# ── Coordinator / client mocks ────────────────────────────────────────────────


def make_mock_coordinator(hass: HomeAssistant, snapshot=None) -> MagicMock:
    """Return a pre-configured mock coordinator."""
    from custom_components.quilt_hp.coordinator import QuiltCoordinator

    coordinator = MagicMock(spec=QuiltCoordinator)
    coordinator.hass = hass
    data = snapshot or make_snapshot()
    coordinator.data = data
    coordinator.spaces_by_id = {s.id: s for s in data.spaces}
    coordinator.idu_by_id = {u.id: u for u in data.indoor_units}
    coordinator.odu_by_id = {u.id: u for u in data.outdoor_units}
    coordinator.last_update_success = True
    coordinator.client = MagicMock()
    coordinator.async_set_space = AsyncMock()
    coordinator.async_set_indoor_unit = AsyncMock()
    coordinator.async_request_refresh = AsyncMock()
    return coordinator
