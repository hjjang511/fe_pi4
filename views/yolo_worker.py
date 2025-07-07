from PyQt5.QtCore import QThread, pyqtSignal
from ultralytics import YOLO
import cv2
import numpy as np
import platform
# from picamera2 import Picamera2

class YoloWorker(QThread):
    detection_result = pyqtSignal(str)  # Gửi tên sản phẩm

    def __init__(self, model_path, source="usb0", threshold=0.5):
        super().__init__()
        self.model = YOLO(model_path)
        self.threshold = threshold
        self.running = True
        self.source = source

        self.is_picamera = "picamera" in source

        if self.is_picamera:

            self.picam2 = Picamera2()
            self.picam2.configure(self.picam2.create_video_configuration(
                main={"format": 'RGB888', "size": (640, 480)}
            ))
            self.picam2.start()
        else:
            # Default: usb0 → index 0
            index = int(source.replace("usb", ""))
            self.cap = cv2.VideoCapture(index)

    def run(self):
        while self.running:
            # Read frame
            if self.is_picamera:
                frame = self.picam2.capture_array()
            else:
                ret, frame = self.cap.read()
                if not ret:
                    continue

            # YOLO inference
            results = self.model(frame, imgsz=416, device="cpu")[0]
            for det in results.boxes:
                conf = det.conf.item()
                if conf < self.threshold:
                    continue
                cls_name = self.model.names[int(det.cls.item())]
                self.detection_result.emit(cls_name)

    def stop(self):
        self.running = False
        if self.is_picamera:
            self.picam2.stop()
        else:
            self.cap.release()
        self.quit()
