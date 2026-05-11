"""Climate platform for Quilt Heat Pump — one entity per Space."""

from __future__ import annotations

import math
from typing import Any, override

from homeassistant.components.climate import (
    ATTR_TARGET_TEMP_HIGH,
    ATTR_TARGET_TEMP_LOW,
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from quilt_hp.models.enums import HVACMode as QHVACMode, HVACState as QHVACState
from quilt_hp.models.space import Space

from .const import DOMAIN
from .coordinator import QuiltCoordinator
from .entity import QuiltEntity, idu_device_info

# ── Mode maps ─────────────────────────────────────────────────────────────────

_Q_TO_HA: dict[QHVACMode, HVACMode] = {
    QHVACMode.STANDBY: HVACMode.OFF,
    QHVACMode.COOL: HVACMode.COOL,
    QHVACMode.HEAT: HVACMode.HEAT,
    QHVACMode.AUTO: HVACMode.HEAT_COOL,
    QHVACMode.FAN: HVACMode.FAN_ONLY,
    QHVACMode.FALLBACK_AUTO: HVACMode.HEAT_COOL,
    QHVACMode.FALLBACK_OFF: HVACMode.OFF,
}

_HA_TO_Q: dict[HVACMode, QHVACMode] = {
    HVACMode.OFF: QHVACMode.STANDBY,
    HVACMode.COOL: QHVACMode.COOL,
    HVACMode.HEAT: QHVACMode.HEAT,
    HVACMode.HEAT_COOL: QHVACMode.AUTO,
    HVACMode.FAN_ONLY: QHVACMode.FAN,
}

_Q_STATE_TO_HA_ACTION: dict[QHVACState, HVACAction] = {
    QHVACState.STANDBY: HVACAction.IDLE,
    QHVACState.COOL: HVACAction.COOLING,
    QHVACState.HEAT: HVACAction.HEATING,
    QHVACState.DRIFT: HVACAction.IDLE,
    QHVACState.FAN: HVACAction.FAN,
    QHVACState.COOL_DEFERRED: HVACAction.COOLING,
    QHVACState.HEAT_DEFERRED: HVACAction.HEATING,
    QHVACState.FAN_DEFERRED: HVACAction.FAN,
    QHVACState.COOL_PREPARING: HVACAction.COOLING,
    QHVACState.HEAT_PREPARING: HVACAction.HEATING,
}


def _normalize_temperature(value: float | None) -> float | None:
    if value is None or math.isnan(value):
        return None
    return value


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up climate entities from a config entry."""
    coordinator: QuiltCoordinator = hass.data[DOMAIN][entry.entry_id]
    snapshot = coordinator.data

    first_idu_for_space: dict[str, str] = {}
    for idu in snapshot.indoor_units:
        if idu.space_id and idu.space_id not in first_idu_for_space:
            first_idu_for_space[idu.space_id] = idu.id

    entities = [
        QuiltClimateEntity(coordinator, space.id, first_idu_for_space[space.id])
        for space in snapshot.spaces
        if space.is_room and space.id in first_idu_for_space
    ]
    async_add_entities(entities)


class QuiltClimateEntity(QuiltEntity, ClimateEntity):
    """Climate entity representing a Quilt space (room)."""

    _attr_temperature_unit: UnitOfTemperature = UnitOfTemperature.CELSIUS
    _attr_supported_features: ClimateEntityFeature = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.TARGET_TEMPERATURE_RANGE
    )
    _attr_translation_key: str = "climate"

    def __init__(
        self, coordinator: QuiltCoordinator, space_id: str, idu_id: str
    ) -> None:
        """Initialize the climate entity."""
        super().__init__(coordinator)
        self._space_id: str = space_id
        self._idu_id: str = idu_id
        self._attr_unique_id: str = f"quilt_space_climate_{space_id}"
        self._attr_name: str | None = None  # use device name as entity name
        self._attr_hvac_modes: list[HVACMode] = list(_HA_TO_Q.keys())

    @property
    def _space(self) -> Space:
        return self.coordinator.spaces_by_id[self._space_id]

    @property
    @override
    def device_info(self) -> DeviceInfo:
        idu = self.coordinator.idu_by_id[self._idu_id]
        space = self._space
        return idu_device_info(idu, space)

    @property
    @override
    def hvac_mode(self) -> HVACMode:
        return _Q_TO_HA.get(self._space.controls.hvac_mode, HVACMode.OFF)

    @property
    @override
    def hvac_action(self) -> HVACAction | None:
        return _Q_STATE_TO_HA_ACTION.get(self._space.state.hvac_state)

    @property
    def _is_explicit_off_mode(self) -> bool:
        return self._space.controls.hvac_mode in (
            QHVACMode.STANDBY,
            QHVACMode.FALLBACK_OFF,
        )

    @property
    def _supports_setpoint_display(self) -> bool:
        return self.hvac_mode in (HVACMode.HEAT, HVACMode.COOL, HVACMode.HEAT_COOL)

    @property
    def _active_comfort_setting(self) -> Any | None:
        comfort_setting_id_or_none = getattr(
            self._space.controls, "comfort_setting_id_or_none", None
        )
        comfort_setting_id = (
            comfort_setting_id_or_none
            if isinstance(comfort_setting_id_or_none, str)
            else self._space.controls.comfort_setting_id or None
        )
        if comfort_setting_id is None:
            return None
        comfort_settings = getattr(self.coordinator.data, "comfort_settings", ())
        return next(
            (cs for cs in comfort_settings if cs.id == comfort_setting_id), None
        )

    @property
    def _effective_setpoints(self) -> tuple[float | None, float | None]:
        heat = _normalize_temperature(self._space.controls.heating_setpoint_c)
        cool = _normalize_temperature(self._space.controls.cooling_setpoint_c)

        has_sentinel = getattr(
            self._space.controls, "has_standby_sentinel_setpoints", False
        )
        if not isinstance(has_sentinel, bool) or not has_sentinel:
            return heat, cool

        comfort_setting = self._active_comfort_setting
        if comfort_setting is not None and not getattr(
            comfort_setting, "has_placeholder_setpoints", False
        ):
            heat = _normalize_temperature(comfort_setting.heating_setpoint_c)
            cool = _normalize_temperature(comfort_setting.cooling_setpoint_c)
            return heat, cool

        missing_setpoint = getattr(self._space.state, "has_missing_setpoint", False)
        if not missing_setpoint:
            setpoint = _normalize_temperature(self._space.state.setpoint_c)
            if (
                self._space.controls.hvac_mode == QHVACMode.HEAT
                and setpoint is not None
            ):
                heat = setpoint
            if (
                self._space.controls.hvac_mode == QHVACMode.COOL
                and setpoint is not None
            ):
                cool = setpoint
        return heat, cool

    @property
    @override
    def current_temperature(self) -> float | None:
        missing_ambient = getattr(
            self._space.state, "has_missing_ambient_temperature", False
        )
        if missing_ambient:
            return None
        return _normalize_temperature(self._space.state.ambient_temperature_c)

    @property
    @override
    def target_temperature(self) -> float | None:
        if self._is_explicit_off_mode or not self._supports_setpoint_display:
            return None
        heat, cool = self._effective_setpoints
        mode = self._space.controls.hvac_mode
        if mode == QHVACMode.COOL:
            return cool
        if mode == QHVACMode.HEAT:
            return heat
        return None

    @property
    @override
    def target_temperature_high(self) -> float | None:
        if self._is_explicit_off_mode or not self._supports_setpoint_display:
            return None
        _, cool = self._effective_setpoints
        return cool

    @property
    @override
    def target_temperature_low(self) -> float | None:
        if self._is_explicit_off_mode or not self._supports_setpoint_display:
            return None
        heat, _ = self._effective_setpoints
        return heat

    @override
    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        quilt_mode = _HA_TO_Q[hvac_mode]
        await self.coordinator.async_set_space(self._space, mode=quilt_mode)
        await self.coordinator.async_request_refresh()

    @override
    async def async_set_temperature(self, **kwargs: Any) -> None:
        heat_sp = kwargs.get(ATTR_TARGET_TEMP_LOW)
        cool_sp = kwargs.get(ATTR_TARGET_TEMP_HIGH)

        if (temp := kwargs.get(ATTR_TEMPERATURE)) is not None:
            if self.hvac_mode == HVACMode.HEAT:
                heat_sp = temp
            else:
                cool_sp = temp

        await self.coordinator.async_set_space(
            self._space,
            heat_setpoint_c=heat_sp,
            cool_setpoint_c=cool_sp,
        )
        await self.coordinator.async_request_refresh()
