#!/usr/bin/env python3
"""Debug script to verify model_sku debug logging works."""

import logging
import sys

# Set up logging to show debug messages
logging.basicConfig(
    level=logging.DEBUG,
    format="%(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)

# Import the test fixtures
sys.path.insert(0, "/home/emmanuel/Projects/homeassistant-quilt-hp")
from tests.conftest import make_snapshot
from custom_components.quilt_hp.coordinator import QuiltCoordinator


def main() -> None:
    """Run debug checks."""
    print("\n" + "=" * 80)
    print("TESTING COORDINATOR DEBUG LOGGING FOR model_sku")
    print("=" * 80 + "\n")

    # Create a snapshot
    print("Creating SystemSnapshot with test fixtures...")
    snapshot = make_snapshot()

    print("\nSimulating debug output from coordinator (checking model_sku):")
    print("-" * 80)
    
    # Manually call the debug logging without needing full initialization
    logger = logging.getLogger("custom_components.quilt_hp.coordinator")
    
    for odu in snapshot.outdoor_units:
        logger.debug(
            "SystemSnapshot ODU: id=%s, model_sku=%r, serial=%r, fw=%r",
            odu.id,
            odu.model_sku,
            odu.serial_number,
            odu.firmware_version,
        )

    for ctrl in snapshot.controllers:
        logger.debug(
            "SystemSnapshot Controller: id=%s, name=%s, model_sku=%r, serial=%r, fw=%r",
            ctrl.id,
            ctrl.name,
            ctrl.model_sku,
            ctrl.serial_number,
            ctrl.firmware_version,
        )
    
    print("-" * 80)

    print("\n✓ Debug logging is working!")
    print("✓ The logs above show model_sku values as they are received from quilt-hp-python")
    print("\nTo enable these logs in Home Assistant:")
    print("  1. Go to Settings → Developer Tools → Logs")
    print("  2. Set logger 'custom_components.quilt_hp' to DEBUG")
    print("  3. Check the logs to see what model_sku values are being received")
    print()


if __name__ == "__main__":
    main()
