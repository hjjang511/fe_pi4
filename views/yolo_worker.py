import csv
import os
from PyQt5.QtCore import QThread, pyqtSignal
from ultralytics import YOLO
import cv2
import time
import numpy as np
from collections import defaultdict, deque
# from picamera2 import Picamera2

class YoloWorker(QThread):
    # Emit: action, label, vao, ra, current_quantity
    detection_result = pyqtSignal(str, str, int, int, int)

    def __init__(self, model_path, source=0, threshold=0.7, parent=None):
        super().__init__(parent)
        self.model = YOLO(model_path)
        self.threshold = threshold
        self.source = source
        self.running = False
        self.cap = cv2.VideoCapture(source)

        # Config Smart Cart
        self.ROI_BOX = (107, 0, 533, 480)
        self.TRAJECTORY_HISTORY = 10
        self.MIN_MOVEMENT_THRESHOLD = 20
        self.ACTION_CONFIRM_FRAMES = 3
        self.VERTICAL_WEIGHT = 1.5
        self.action_cooldown = 1.0

        # Tracking state
        self.total_vao = defaultdict(int)
        self.total_ra = defaultdict(int)
        self.object_trajectories = defaultdict(lambda: deque(maxlen=self.TRAJECTORY_HISTORY))
        self.confidence_history = defaultdict(lambda: deque(maxlen=5))
        self.pending_actions = defaultdict(dict)
        self.action_confirm_counter = defaultdict(int)
        self.last_action_time = defaultdict(float)
        self.object_labels = {}

    def detect_action(self, trajectory):
        if len(trajectory) < self.TRAJECTORY_HISTORY // 2:
            return None

        dx, dy = self.calculate_movement_vector(trajectory)
        if dx is None or dy is None:
            return None

        movement_distance = np.sqrt(dx**2 + (dy * self.VERTICAL_WEIGHT)**2)
        if movement_distance < self.MIN_MOVEMENT_THRESHOLD:
            return None

        roi_x1, roi_y1, roi_x2, roi_y2 = self.ROI_BOX

        start_point = trajectory[0]
        end_point = trajectory[-1]

        # VAO: đi từ ngoài vào
        if dy > 0:
            start_outside = not (roi_x1 <= start_point[0] <= roi_x2 and roi_y1 <= start_point[1] <= roi_y2)
            end_inside = (roi_x1 <= end_point[0] <= roi_x2 and roi_y1 <= end_point[1] <= roi_y2)
            if start_outside and end_inside:
                return "VAO"

        # RA: đi từ trong ra
        if dy < 0:
            start_inside = (roi_x1 <= start_point[0] <= roi_x2 and roi_y1 <= start_point[1] <= roi_y2)
            end_outside = not (roi_x1 <= end_point[0] <= roi_x2 and roi_y1 <= end_point[1] <= roi_y2)
            if start_inside and end_outside:
                return "RA"

        return None


    def run(self):
        self.running = True
        while self.running:
            # if self.use_picamera:
            #     # 📷 Lấy ảnh từ PiCamera2
            #     frame = self.picam2.capture_array()
            # else:
            # 📷 Lấy ảnh từ OpenCV camera
            ret, frame = self.cap.read()
            if not ret:
                continue

            results = self.model.track(frame, persist=True, verbose=False)
            boxes = results[0].boxes
            current_time = time.time()

            if not boxes or boxes.id is None or boxes.id.numel() == 0:
                detected_ids = set()
            else:
                ids = boxes.id.cpu().numpy().astype(int)
                boxes_xyxy = boxes.xyxy.cpu().numpy()
                classes = boxes.cls.cpu().numpy().astype(int)
                confidences = boxes.conf.cpu().numpy()
                detected_ids = set(ids)

                for i, obj_id in enumerate(ids):
                    x1, y1, x2, y2 = boxes_xyxy[i]
                    cls_id = classes[i]
                    confidence = confidences[i]
                    label = self.model.names[cls_id]
                    obj_id = int(obj_id)

                    # Chỉ xử lý nếu đủ threshold
                    if confidence < self.threshold:
                        continue

                    self.object_labels[obj_id] = label
                    cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
                    self.object_trajectories[obj_id].append((cx, cy))
                    self.confidence_history[obj_id].append(confidence)

                    # Check action
                    action = self.detect_action(self.object_trajectories[obj_id])
                    if action:
                        if current_time - self.last_action_time[obj_id] > self.action_cooldown:
                            if obj_id not in self.pending_actions or self.pending_actions[obj_id].get("type") != action:
                                self.pending_actions[obj_id] = {"type": action, "label": label}
                                self.action_confirm_counter[obj_id] = 1
                            else:
                                self.action_confirm_counter[obj_id] += 1

                            if self.action_confirm_counter[obj_id] >= self.ACTION_CONFIRM_FRAMES:
                                if action == "VAO":
                                    self.total_vao[label] += 1
                                    add_to_cart(label)


                                else:
                                    self.total_ra[label] += 1
                                    remove_from_cart(label)


                                current_quantity = max(0, self.total_vao[label] - self.total_ra[label])

                                self.detection_result.emit(
                                    action,
                                    label,
                                    self.total_vao[label],
                                    self.total_ra[label],
                                    current_quantity
                                )

                                self.last_action_time[obj_id] = current_time
                                self.pending_actions.pop(obj_id, None)
                                self.action_confirm_counter[obj_id] = 0

            self.msleep(50)

    def stop(self):
        self.running = False
        self.wait()
        if hasattr(self, "cap"):
            self.cap.release()

def add_to_cart(item_name, quantity=1, cart_file="data/cart_data.csv"):
    print(f"[DEBUG] add_to_cart: {item_name}, quantity={quantity}")
    cart = []
    fieldnames = ["index","image","name","description","aisle","price","quantity","discount"]

    # Đọc file nếu tồn tại
    if os.path.exists(cart_file):
        with open(cart_file, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                cart.append(row)

    # Tìm xem sản phẩm đã có trong cart chưa
    found = False
    for row in cart:
        if row["name"] == item_name:
            row["quantity"] = str(int(row["quantity"]) + quantity)
            found = True
            break

    if not found:
        product_info = get_product_info(item_name)
        new_index = len(cart) + 1
        cart.append({
            "index": str(new_index),
            "image": product_info["image"],
            "name": item_name,
            "description": product_info["description"],
            "aisle": product_info["aisle"],
            "price": product_info["price"],
            "quantity": str(quantity),
            "discount": str(product_info["discount"])
        })

    # Ghi lại file
    with open(cart_file, "w", newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(cart)


def remove_from_cart(item_name, quantity=1, cart_file="data/cart_data.csv"):
    if not os.path.exists(cart_file):
        return
    
    cart = []
    fieldnames = ["index","image","name","description","aisle","price","quantity","discount"]

    with open(cart_file, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            cart.append(row)

    for row in cart:
        if row["name"] == item_name:
            new_qty = max(0, int(row["quantity"]) - quantity)
            row["quantity"] = str(new_qty)
            break

    # Xóa các item có quantity = 0
    cart = [row for row in cart if int(row["quantity"]) > 0]

    # Re-index lại cho đẹp
    for i, row in enumerate(cart, start=1):
        row["index"] = str(i)

    with open(cart_file, "w", newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(cart)

def get_product_info(item_name, product_file="data/shop_data.csv"):
    """
    Lấy thông tin sản phẩm từ file shop_data.csv theo tên sản phẩm.
    Nếu không tìm thấy thì trả về default.
    """
    if not os.path.exists(product_file):
        return {
            "error": "Product file not found"
        }

    with open(product_file, newline='', encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            name = row[2].strip().lower()
            if name == item_name.strip().lower():
                return {
                    "image": row[1],
                    "description": row[4],
                    "aisle": row[3],
                    "price": float(row[6]),
                    "quantity": int(row[5]),
                    "discount": float(row[7])
                }



