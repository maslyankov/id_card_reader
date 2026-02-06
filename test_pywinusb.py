"""
Minimal pywinusb test - run this on Windows with the DESKO reader connected.
This uses the exact same pattern as the original working code.
"""
import sys
if sys.platform != 'win32':
    print("This script only works on Windows")
    sys.exit(1)

import pywinusb.hid as hid
from time import sleep

GLOBAL = False

def sample_handler(data):
    global GLOBAL
    print(f"  callback fired: len={len(data)}, first_bytes={data[:5]}")
    empty_row = [0, 48, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    if data not in [empty_row]:
        print(f"  -> GOT REAL DATA!")
        GLOBAL = True

# Method 1: find_all_hid_devices
print("=== Method 1: find_all_hid_devices() ===")
all_hids = hid.find_all_hid_devices()
print(f"Total HID devices: {len(all_hids)}")
desko_devices = []
for i, dev in enumerate(all_hids):
    if dev.vendor_id == 0x0744 and dev.product_id == 0x001d:
        print(f"  DESKO #{len(desko_devices)}: {dev.vendor_name} {dev.product_name} "
              f"(vID=0x{dev.vendor_id:04x}, pID=0x{dev.product_id:04x})")
        desko_devices.append(dev)

# Method 2: HidDeviceFilter
print(f"\n=== Method 2: HidDeviceFilter ===")
target_filter = hid.HidDeviceFilter(vendor_id=0x0744, product_id=0x001d)
filtered = target_filter.get_devices()
print(f"Filtered devices: {len(filtered)}")
for i, dev in enumerate(filtered):
    print(f"  #{i}: {dev.vendor_name} {dev.product_name} "
          f"(vID=0x{dev.vendor_id:04x}, pID=0x{dev.product_id:04x})")

# Try to open and read from each method
devices_to_try = desko_devices if desko_devices else filtered
if not devices_to_try:
    print("\nNo DESKO devices found!")
    sys.exit(1)

for idx, device in enumerate(devices_to_try):
    print(f"\n=== Trying device #{idx} ===")
    GLOBAL = False
    try:
        device.set_raw_data_handler(sample_handler)
        device.open()
        print("Device opened. Scan a document within 30 seconds...")

        for i in range(60):
            sleep(0.5)
            if GLOBAL:
                print(f"Data received after {i*0.5}s!")
                break
        else:
            print("Timeout - no data received")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        device.close()
        print("Device closed.")

    if GLOBAL:
        break
