import cv2
import time
import csv
import os
from ultralytics import YOLO
from PyQt5.QtCore import QThread, pyqtSignal
from collections import defaultdict


class YoloWorker(QThread):
    """
    YoloWorker: Theo dõi đối tượng trong ROI
    - Đếm số vật trong ROI = số lần vào - số lần ra
    - Ghi nhận số lượng cao nhất đạt được
    - Cập nhật CSV giỏ hàng
    - Phát signal cho UI: (label, current_count, max_count, action)
    """

    detection_result = pyqtSignal(str, int, int, str)  
    # label, current_count, max_count, action(“VAO”/“RA”)

    def __init__(self, model_path="my_model.pt", source=0, resolution=(640, 480),
                 roi_box=(160, 120, 480, 360), max_missing_frames=30,
                 cart_file="data/cart_data.csv", shop_file="data/shop_data.csv",
                 parent=None):
        super().__init__(parent)

        # Config
        self.model = YOLO(model_path)
        self.source = source
        self.resolution = resolution
        self.ROI_BOX = roi_box
        self.MAX_MISSING_FRAMES = max_missing_frames

        # Camera
        self.cap = cv2.VideoCapture(source)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, resolution[0])
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, resolution[1])

        # Files
        self.cart_file = cart_file
        self.shop_file = shop_file
        os.makedirs(os.path.dirname(self.cart_file), exist_ok=True)

        # State
        self.running = False
        self.object_counts = defaultdict(int)      # label -> current_count
        self.max_counts = defaultdict(int)         # label -> max_count
        self.object_in_roi_state = {}              # id -> bool
        self.disappeared_counter = defaultdict(int)

    # ================= CSV helpers =================
    def add_to_cart(self, item_name, quantity=1):
        cart = []
        fieldnames = ["index", "image", "name", "description",
                      "aisle", "price", "quantity", "discount"]

        if os.path.exists(self.cart_file):
            with open(self.cart_file, newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                cart.extend(reader)

        found = False
        for row in cart:
            if row["name"].strip().lower() == item_name.strip().lower():
                row["quantity"] = str(int(row["quantity"]) + quantity)
                found = True
                break

        if not found:
            product_info = self.get_product_info(item_name)
            new_index = len(cart) + 1
            cart.append({
                "index": str(new_index),
                "image": str(product_info.get("image", "")),
                "name": item_name,
                "description": str(product_info.get("description", "")),
                "aisle": str(product_info.get("aisle", "")),
                "price": str(product_info.get("price", 0.0)),
                "quantity": str(quantity),
                "discount": str(product_info.get("discount", 0.0)),
            })

        with open(self.cart_file, "w", newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(cart)

    def remove_from_cart(self, item_name, quantity=1):
        if not os.path.exists(self.cart_file):
            return

        cart = []
        fieldnames = ["index", "image", "name", "description",
                      "aisle", "price", "quantity", "discount"]

        with open(self.cart_file, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            cart.extend(reader)

        for row in cart:
            if row["name"].strip().lower() == item_name.strip().lower():
                new_qty = max(0, int(row["quantity"]) - quantity)
                row["quantity"] = str(new_qty)
                break

        cart = [row for row in cart if int(row["quantity"]) > 0]

        for i, row in enumerate(cart, start=1):
            row["index"] = str(i)

        with open(self.cart_file, "w", newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(cart)

    def get_product_info(self, item_name):
        if not os.path.exists(self.shop_file):
            return {}
        try:
            with open(self.shop_file, newline='', encoding="utf-8") as f:
                reader = csv.reader(f)
                for row in reader:
                    if len(row) < 8:
                        continue
                    name = row[2].strip().lower()
                    if name == item_name.strip().lower():
                        return {
                            "image": row[1],
                            "description": row[4],
                            "aisle": row[3],
                            "price": float(row[6]),
                            "quantity": int(row[5]),
                            "discount": float(row[7]),
                        }
        except Exception:
            return {}
        return {}

    # ================= Main loop =================
    def run(self):
        self.running = True
        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                continue

            results = self.model.track(frame, persist=True, verbose=False)
            boxes = results[0].boxes

            if not boxes or boxes.id is None or boxes.id.numel() == 0:
                detected_ids = set()
            else:
                ids = boxes.id.cpu().numpy().astype(int)
                boxes_xyxy = boxes.xyxy.cpu().numpy()
                classes = boxes.cls.cpu().numpy().astype(int)
                detected_ids = set(ids)

                for i, obj_id in enumerate(ids):
                    x1, y1, x2, y2 = boxes_xyxy[i]
                    cls_id = classes[i]
                    label = self.model.names[cls_id]
                    obj_id = int(obj_id)

                    cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
                    rx1, ry1, rx2, ry2 = self.ROI_BOX
                    in_roi = rx1 <= cx <= rx2 and ry1 <= cy <= ry2

                    self.disappeared_counter[obj_id] = 0
                    if obj_id not in self.object_in_roi_state:
                        self.object_in_roi_state[obj_id] = False

                    if in_roi and not self.object_in_roi_state[obj_id]:
                        # Object vừa vào ROI
                        self.object_in_roi_state[obj_id] = True
                        self.object_counts[label] += 1
                        if self.object_counts[label] > self.max_counts[label]:
                            self.max_counts[label] = self.object_counts[label]
                        self.add_to_cart(label, 1)
                        self._emit_result(label, "VAO")

                    elif not in_roi and self.object_in_roi_state[obj_id]:
                        # Object vừa rời ROI
                        self.object_in_roi_state[obj_id] = False
                        self.object_counts[label] = max(0, self.object_counts[label] - 1)
                        self.remove_from_cart(label, 1)
                        self._emit_result(label, "RA")

            # Tăng bộ đếm mất tích
            for obj_id in list(self.disappeared_counter):
                if obj_id not in (detected_ids if 'detected_ids' in locals() else set()):
                    self.disappeared_counter[obj_id] += 1
                    if self.disappeared_counter[obj_id] > self.MAX_MISSING_FRAMES:
                        self.disappeared_counter.pop(obj_id, None)

            self.msleep(30)

    def _emit_result(self, label, action):
        current = self.object_counts[label]
        max_seen = self.max_counts[label]
        try:
            self.detection_result.emit(label, current, max_seen, action)
        except Exception:
            pass

    def stop(self):
        self.running = False
        self.wait()
        if hasattr(self, "cap") and self.cap is not None:
            try:
                self.cap.release()
            except Exception:
                pass
