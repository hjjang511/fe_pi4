# ble_scanner.py
import asyncio
from bleak import BleakScanner

TARGET_NAMES = ["0-0", "0-30", "15-30"]
latest_rssi = {name: None for name in TARGET_NAMES}

async def scan_once(timeout=2.0):
    scanner = BleakScanner()

    def callback(device, advertisement_data):
        name = advertisement_data.local_name or device.name
        if name in TARGET_NAMES:
            latest_rssi[name] = device.rssi

    scanner.register_detection_callback(callback)
    await scanner.start()
    await asyncio.sleep(timeout)
    await scanner.stop()

    return {name: latest_rssi.get(name, -100) for name in TARGET_NAMES}
