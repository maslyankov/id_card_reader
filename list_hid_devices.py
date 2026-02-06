"""Debug script: list all HID devices seen by hidapi."""
import hid

devices = hid.enumerate()
if not devices:
    print("No HID devices found at all.")
else:
    print(f"Found {len(devices)} HID device(s):\n")
    for i, dev in enumerate(devices):
        print(f"--- Device {i} ---")
        print(f"  manufacturer_string: {dev.get('manufacturer_string')!r}")
        print(f"  product_string:      {dev.get('product_string')!r}")
        print(f"  vendor_id:           0x{dev.get('vendor_id', 0):04x}")
        print(f"  product_id:          0x{dev.get('product_id', 0):04x}")
        print(f"  path:                {dev.get('path')!r}")
        print(f"  usage_page:          0x{dev.get('usage_page', 0):04x}")
        print(f"  usage:               0x{dev.get('usage', 0):04x}")
        print()
