from PyQt5.QtCore import QThread, pyqtSignal
import asyncio
from rssi_positon.receive_ble import scan_once

class BLEScannerThread(QThread):
    rssi_signal = pyqtSignal(dict)

    def run(self):
        rssi_dict = asyncio.run(scan_once())
        self.rssi_signal.emit(rssi_dict)
