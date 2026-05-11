#!/usr/bin/env python3
"""Debug script to check model_sku values for ODUs and Controllers."""

import logging
import sys
from unittest.mock import MagicMock

# Set up logging to show debug messages
logging.basicConfig(
    level=logging.DEBUG,
    format="%(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)

# Import after setting up logging
from quilt_hp.models.outdoor_unit import OutdoorUnit, OutdoorUnitPerformanceData
from quilt_hp.models.controller import Controller
from quilt_hp.models.indoor_unit import IndoorUnit, IndoorUnitSettings
from quilt_hp.models.qsm import QuiltSmartModule
from quilt_hp.models.space import Space, SpaceControls, SpaceSettings, SpaceState
from quilt_hp.models.system import SystemSnapshot
from custom_components.quilt_hp.entity import odu_device_info, controller_device_info

# Create test data matching the test fixtures
def make_odu(
    odu_id: str = "odu-001",
    model_sku: str | None = "QHP-1234",
) -> OutdoorUnit:
    """Create an OutdoorUnit for testing."""
    return OutdoorUnit(
        id=odu_id,
        system_id="sys-001",
        space_id="space-001",
        hvac_state=2,
        model_sku=model_sku,
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


def make_controller(
    ctrl_id: str = "ctrl-001",
    model_sku: str | None = "QC-5678",
) -> Controller:
    """Create a Controller for testing."""
    return Controller(
        id=ctrl_id,
        system_id="sys-001",
        space_id="space-001",
        name="Living Room Dial",
        raw_thermistor_c=20.0,
        pcb_temperature_a_c=25.0,
        pcb_temperature_b_c=25.0,
        calibrated_ambient_c=20.0,
        wifi_ssid="MyWifi",
        wifi_ip="192.168.1.100",
        wifi_signal_dbm=-45,
        wifi_freq_mhz=2400,
        wifi_last_seen=None,
        ap_wifi=None,
        p2p_wifi=None,
        remote_sensor_mode=0,
        software_update_info_id=None,
        firmware_update_info_id=None,
        serial_number="SN-ctrl-001",
        model_sku=model_sku,
        firmware_version="2.0.1",
        state_updated_at=None,
    )


def main() -> None:
    """Run debug checks."""
    print("\n" + "=" * 80)
    print("TESTING WITH model_sku POPULATED")
    print("=" * 80 + "\n")

    odu_with_model = make_odu(model_sku="QHP-1234")
    ctrl_with_model = make_controller(model_sku="QC-5678")

    print("Building ODU device info with model_sku='QHP-1234':")
    odu_info = odu_device_info(odu_with_model)
    print(f"  Result: model={odu_info['model']}\n")

    print("Building Controller device info with model_sku='QC-5678':")
    ctrl_info = controller_device_info(ctrl_with_model)
    print(f"  Result: model={ctrl_info['model']}\n")

    print("\n" + "=" * 80)
    print("TESTING WITH model_sku = None")
    print("=" * 80 + "\n")

    odu_no_model = make_odu(model_sku=None)
    ctrl_no_model = make_controller(model_sku=None)

    print("Building ODU device info with model_sku=None:")
    odu_info = odu_device_info(odu_no_model)
    print(f"  Result: model={odu_info['model']}\n")

    print("Building Controller device info with model_sku=None:")
    ctrl_info = controller_device_info(ctrl_no_model)
    print(f"  Result: model={ctrl_info['model']}\n")

    print("\n" + "=" * 80)
    print("TESTING WITH model_sku = '' (EMPTY STRING)")
    print("=" * 80 + "\n")

    odu_empty_model = make_odu(model_sku="")
    ctrl_empty_model = make_controller(model_sku="")

    print("Building ODU device info with model_sku='' (empty string):")
    odu_info = odu_device_info(odu_empty_model)
    print(f"  Result: model={odu_info['model']}\n")

    print("Building Controller device info with model_sku='' (empty string):")
    ctrl_info = controller_device_info(ctrl_empty_model)
    print(f"  Result: model={ctrl_info['model']}\n")

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print("✓ If model_sku is populated (non-None, non-empty), it should display")
    print("✓ If model_sku is None or empty, fallbacks should display:")
    print("  - ODU fallback: 'Quilt Outdoor Unit'")
    print("  - Controller fallback: 'Quilt Dial'")
    print()


if __name__ == "__main__":
    main()
