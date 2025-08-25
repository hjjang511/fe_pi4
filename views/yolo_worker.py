from PyQt5.QtCore import QThread, pyqtSignal
from ultralytics import YOLO
import cv2

class YoloWorker(QThread):
    detection_result = pyqtSignal(str)  # Emit tên sản phẩm được detect

    def __init__(self, model_path, source="usb0", threshold=0.5, parent=None):
        super().__init__(parent)
        self.model = YOLO(model_path)
        self.threshold = threshold
        self.source = source
        self.running = False

        # Nếu muốn dùng PiCamera thì mở code này
        self.is_picamera = "picamera" in source
        if not self.is_picamera:
            # Default: usb0 → index 0
            index = int(source.replace("usb", ""))
            self.cap = cv2.VideoCapture(index)

    def run(self):
        self.running = True
        while self.running:
            # Lấy frame
            if self.is_picamera:
                frame = self.picam2.capture_array()
            else:
                ret, frame = self.cap.read()
                if not ret:
                    continue

            # YOLO inference
            results = self.model(frame, imgsz=416, device="cpu")[0]
            for det in results.boxes:
                conf = float(det.conf.item())
                if conf < self.threshold:
                    continue
                cls_name = self.model.names[int(det.cls.item())]
                self.detection_result.emit(cls_name)

            self.msleep(200)  # tránh CPU 100%

    def stop(self):
        self.running = False
        self.wait()  # đảm bảo thread dừng hẳn
        if not self.is_picamera and hasattr(self, "cap"):
            self.cap.release()
