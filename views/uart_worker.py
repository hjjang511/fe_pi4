import serial
from PyQt5.QtCore import QThread, pyqtSignal

class UartWorker(QThread):
    data_received = pyqtSignal(str)   # Khai báo signal

    def __init__(self, port="COM3", baudrate=9600, parent=None):
        super().__init__(parent)
        self.port = port
        self.baudrate = baudrate
        self._running = True
        self.ser = None

    def run(self):
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=1)
            print(f"[UART] Listening on {self.port} at {self.baudrate} baud...")
        except Exception as e:
            print(f"[UART] Cannot open port: {e}")
            return

        while self._running and self.ser.is_open:
            try:
                line = self.ser.readline().decode(errors="ignore").strip()
                if line:
                    print(f"[UART] {line}")
                    self.data_received.emit(line)  # phát signal
            except Exception as e:
                print(f"[UART] Error: {e}")
                break

        if self.ser and self.ser.is_open:
            self.ser.close()
            print("[UART] Port closed.")

    def stop(self):
        self._running = False
        self.wait()
