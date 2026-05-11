# Debugging Model Number Display Issue

This document explains how to debug why outdoor units and controllers display "N/A" for their model numbers instead of their actual SKU values.

## Quick Start

To enable debug logging in Home Assistant:

1. Go to **Settings** → **Developer Tools** → **Logs**
2. In the "Log Viewer" section, set the logger level:
   - Logger: `custom_components.quilt_hp`
   - Level: `DEBUG`
3. Click **Start Following**
4. Trigger a coordinator update or restart Home Assistant
5. Check the logs for lines like:
   ```
   SystemSnapshot ODU: id=odu-001, model_sku='QHP-1234', serial='SN-12345', fw='1.2.3'
   SystemSnapshot Controller: id=ctrl-001, name=Living Room Dial, model_sku='QC-5678', serial='SN-ctrl-001', fw='2.0.1'
   ```

## What the Debug Logs Show

### Coordinator Logging
When `QuiltCoordinator.async_set_updated_data()` is called with a new snapshot, you'll see:

```
custom_components.quilt_hp.coordinator - DEBUG - SystemSnapshot ODU: id=odu-001, model_sku='QHP-1234', serial='SN-12345', fw='1.2.3'
custom_components.quilt_hp.coordinator - DEBUG - SystemSnapshot Controller: id=ctrl-001, name=Living Room Dial, model_sku='QC-5678', serial='SN-ctrl-001', fw='2.0.1'
```

This shows **exactly what values are received from quilt-hp-python**.

### Entity Device Info Logging
When a device's `DeviceInfo` is being built, you'll see:

```
custom_components.quilt_hp.entity - DEBUG - ODU device info: id=odu-001, model_sku='QHP-1234', serial='SN-12345', fw='1.2.3'
custom_components.quilt_hp.entity - DEBUG - Controller device info: id=ctrl-001, name=Living Room Dial, model_sku='QC-5678', serial='SN-ctrl-001', fw='2.0.1'
```

## Interpreting the Results

### If `model_sku` has a value like `'QHP-1234'`
✅ **The API is returning the data correctly**
- Home Assistant should display this value in the device info
- If it shows as "N/A", it's a Home Assistant UI rendering issue

### If `model_sku` is `None`
⚠️ **The quilt-hp-python library didn't receive hardware info from the API**
- The fallback will display: "Quilt Outdoor Unit" or "Quilt Dial"
- This suggests the Quilt API response is missing the `outdoor_unit_hardware` or `controller_hardware` fields

### If `model_sku` is an empty string `''`
⚠️ **The API returned an empty string instead of the actual SKU**
- The fallback will still display correctly (empty strings are falsy in Python)
- This suggests the Quilt API is returning incomplete hardware information

## Testing the Debug Logging

Two helper scripts are included to verify the debug logging works:

### 1. `debug_model_sku.py` - Test fallback logic
Tests that the fallback logic works correctly when model_sku is None or empty:

```bash
python3 debug_model_sku.py
```

Output shows:
- Model numbers display correctly when populated
- Fallbacks display when model_sku is None or empty

### 2. `debug_model_sku_logging.py` - Test coordinator logging
Tests the actual debug logging from the coordinator:

```bash
python3 debug_model_sku_logging.py
```

Output shows the debug logs that would appear in Home Assistant when data is received.

## How to Check Yourself

To verify the issue:

1. **Enable debug logging** (see Quick Start above)
2. **Restart Home Assistant** or trigger a coordinator update
3. **Check the logs** in Developer Tools → Logs
4. **Look for lines with `model_sku=`**:
   - If you see a SKU value like `'QHP-1234'`, the API is returning it
   - If you see `None`, the API isn't providing hardware info
   - If you see an empty string `''`, the API is returning incomplete data

## Root Cause Analysis

The issue is in how `quilt-hp-python` deserializes device data:

```python
# From OutdoorUnit.from_proto():
model_sku=hw.attributes.model_sku if hw else None

# From Controller.from_proto():
if hw_map:
    hw = hw_map.get(hw_id)
    if hw is not None:
        a = hw.attributes
        serial = a.serial_number or None
```

The `model_sku` is populated from a "hardware map" that's built from API response fields:
- `HomeDatastoreSystem.outdoor_unit_hardware` for ODUs
- `HomeDatastoreSystem.controller_hardware` for Controllers

**If these aren't in the API response, `model_sku` will be `None`.**

## Next Steps

If the debug logs show `model_sku=None`:

1. **Report to quilt-hp-python** repository with:
   - The debug logs showing `model_sku=None`
   - Your Quilt system configuration (number of units, controllers, etc.)
   - A link to this issue

2. **Or report to Quilt** if the API should include this data but isn't

If the debug logs show a proper SKU value but Home Assistant displays "N/A":
- This is a Home Assistant device registry display issue
- The integration is working correctly
