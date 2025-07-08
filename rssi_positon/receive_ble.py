# ble_scanner.py
import asyncio
from bleak import BleakScanner

TARGET_NAMES = ["0-0", "0-30", "15-30"]

async def scan_once(timeout=2.0):
    latest_rssi = {name: -100 for name in TARGET_NAMES}  # M?c �?nh -100

    def callback(device, advertisement_data):
        name = advertisement_data.local_name or device.name or device.address
        if name in TARGET_NAMES:
            latest_rssi[name] = advertisement_data.rssi  # ? l?y RSSI t? advertisement_data

    # ? d�ng detection_callback trong constructor
    scanner = BleakScanner(detection_callback=callback)
    await scanner.start()
    await asyncio.sleep(timeout)
    await scanner.stop()

    return latest_rssi
