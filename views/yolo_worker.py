import os
import csv
import cv2
import time
from collections import defaultdict, deque
from PyQt5.QtCore import QThread, pyqtSignal
from ultralytics import YOLO


class YoloWorker(QThread):
    """
    Smart Cart YoloWorker - Minimal
    - Track object bằng YOLO
    - Xác nhận hành động vào/ra giỏ dựa trên confidence
    - Pending add/remove (timeout)
    - Mất tích trong ROI => coi như lấy ra
    - Cập nhật CSV giỏ hàng
    - Phát signal detection_result và log_signal
    """

    detection_result = pyqtSignal(str, str, int, int, int)  # action, label, vao, ra, current_qty
    log_signal = pyqtSignal(str)

    def __init__(
        self,
        model_path,
        source=0,
        threshold=0.5,
        resolution=(640, 480),
        roi_box=(160, 120, 480, 360),
        high_confidence=0.7,
        conf_buffer_size=5,
        min_high_conf_frames=3,
        max_missing_frames=30,
        max_missing_frames_in_roi=15,
        action_timeout=2.0,
        cart_file="data/cart_data.csv",
        shop_file="data/shop_data.csv",
        parent=None
    ):
        super().__init__(parent)

        # YOLO model + camera
        self.model = YOLO(model_path)
        self.cap = cv2.VideoCapture(source)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, resolution[0])
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, resolution[1])

        # Config
        self.running = False
        self.ROI_BOX = roi_box
        self.MIN_CONFIDENCE = threshold
        self.HIGH_CONFIDENCE = high_confidence
        self.CONFIDENCE_BUFFER_SIZE = conf_buffer_size
        self.MIN_HIGH_CONF_FRAMES = min_high_conf_frames
        self.MAX_MISSING_FRAMES = max_missing_frames
        self.MAX_MISSING_FRAMES_IN_ROI = max_missing_frames_in_roi
        self.ACTION_TIMEOUT = action_timeout

        # Files
        self.cart_file = cart_file
        self.shop_file = shop_file
        os.makedirs(os.path.dirname(self.cart_file), exist_ok=True)

        # States
        self.products_in_cart = defaultdict(int)
        self.total_added = defaultdict(int)
        self.total_removed = defaultdict(int)

        self.known_ids_in_cart = {}
        self.object_in_cart_state = {}
        self.cart_entry_time = {}

        self.disappeared_counter = defaultdict(int)
        self.cart_missing_counter = defaultdict(int)

        self.confidence_history = defaultdict(lambda: deque(maxlen=self.CONFIDENCE_BUFFER_SIZE))
        self.last_confidence = defaultdict(float)
        self.high_confidence_frames = defaultdict(int)

        self.pending_add_operations = defaultdict(dict)
        self.pending_remove_operations = defaultdict(dict)

        self.total_vao = defaultdict(int)
        self.total_ra = defaultdict(int)

    # ================= CSV helpers =================
    def add_to_cart(self, item_name, quantity=1):
        cart = []
        fieldnames = ["index", "image", "name", "description", "aisle", "price", "quantity", "discount"]

        if os.path.exists(self.cart_file):
            with open(self.cart_file, newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    cart.append(row)

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
        fieldnames = ["index", "image", "name", "description", "aisle", "price", "quantity", "discount"]

        with open(self.cart_file, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                cart.append(row)

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

    # ================= Utils =================
    def _debug(self, msg: str):
        try:
            self.log_signal.emit(msg)
        except Exception:
            pass
        print(msg)

    def _get_avg_confidence(self, oid):
        h = self.confidence_history.get(oid)
        return sum(h) / len(h) if h else 0.0

    def _is_reliable_detection(self, oid, conf):
        avg_conf = self._get_avg_confidence(oid)
        return conf >= self.MIN_CONFIDENCE and avg_conf >= self.MIN_CONFIDENCE

    def _should_confirm_operation(self, oid, conf):
        if conf >= self.HIGH_CONFIDENCE:
            self.high_confidence_frames[oid] += 1
        else:
            self.high_confidence_frames[oid] = max(0, self.high_confidence_frames[oid] - 1)
        return self.high_confidence_frames[oid] >= self.MIN_HIGH_CONF_FRAMES

    def _emit_detection(self, action, label):
        if action == "VAO":
            self.total_vao[label] += 1
        elif action == "RA":
            self.total_ra[label] += 1

        current_qty = max(0, self.total_vao[label] - self.total_ra[label])
        try:
            self.detection_result.emit(action, label, self.total_vao[label], self.total_ra[label], current_qty)
        except Exception:
            pass

    def _forget_id(self, oid):
        self.disappeared_counter.pop(oid, None)
        self.cart_missing_counter.pop(oid, None)
        self.confidence_history.pop(oid, None)
        self.last_confidence.pop(oid, None)
        self.high_confidence_frames.pop(oid, None)
        self.pending_add_operations.pop(oid, None)
        self.pending_remove_operations.pop(oid, None)
        self.object_in_cart_state.pop(oid, None)
        self.cart_entry_time.pop(oid, None)

    # ================= Main loop =================
    def run(self):
        self.running = True
        self._debug("[INFO] YoloWorker started.")

        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                continue

            try:
                results = self.model.track(frame, persist=True, verbose=False)
            except Exception as e:
                self._debug(f"[ERROR] YOLO track error: {e}")
                break

            boxes = results[0].boxes if results and len(results) > 0 else None
            if not boxes or boxes.id is None or boxes.id.numel() == 0:
                detected_ids = set()
            else:
                ids = boxes.id.cpu().numpy().astype(int)
                xyxy = boxes.xyxy.cpu().numpy()
                classes = boxes.cls.cpu().numpy().astype(int)
                confs = boxes.conf.cpu().numpy()
                detected_ids = set(ids)

                for i, oid in enumerate(ids):
                    cls_id = classes[i]
                    conf = float(confs[i])
                    label = self.model.names[cls_id]
                    oid = int(oid)

                    self.confidence_history[oid].append(conf)
                    self.last_confidence[oid] = conf

                    if not self._is_reliable_detection(oid, conf):
                        continue

                    cx, cy = (xyxy[i][0] + xyxy[i][2]) / 2, (xyxy[i][1] + xyxy[i][3]) / 2
                    rx1, ry1, rx2, ry2 = self.ROI_BOX
                    in_cart = (rx1 <= cx <= rx2) and (ry1 <= cy <= ry2)

                    self.disappeared_counter[oid] = 0
                    if oid not in self.object_in_cart_state:
                        self.object_in_cart_state[oid] = False

                    if in_cart:
                        self.cart_missing_counter[oid] = 0
                        if not self.object_in_cart_state[oid]:
                            if oid not in self.pending_add_operations:
                                self.pending_add_operations[oid] = {"label": label, "timestamp": time.time()}
                            if self._should_confirm_operation(oid, conf):
                                self.object_in_cart_state[oid] = True
                                self.known_ids_in_cart[oid] = label
                                self.cart_entry_time[oid] = time.time()
                                self.products_in_cart[label] += 1
                                self.total_added[label] += 1
                                self.add_to_cart(label, 1)
                                self._emit_detection("VAO", label)
                                self.pending_add_operations.pop(oid, None)
                    else:
                        if self.object_in_cart_state[oid]:
                            if oid not in self.pending_remove_operations:
                                self.pending_remove_operations[oid] = {"label": label, "timestamp": time.time()}
                            if self._should_confirm_operation(oid, conf):
                                self.object_in_cart_state[oid] = False
                                if oid in self.known_ids_in_cart:
                                    if self.products_in_cart[label] > 0:
                                        self.products_in_cart[label] -= 1
                                        self.total_removed[label] += 1
                                    self.remove_from_cart(label, 1)
                                    self._emit_detection("RA", label)
                                    self.cart_entry_time.pop(oid, None)
                                self.pending_remove_operations.pop(oid, None)
                        else:
                            self.pending_add_operations.pop(oid, None)

            # Pending timeout
            now = time.time()
            for oid in list(self.pending_add_operations.keys()):
                if now - self.pending_add_operations[oid]["timestamp"] > self.ACTION_TIMEOUT:
                    self.pending_add_operations.pop(oid, None)
                    self.high_confidence_frames[oid] = 0
            for oid in list(self.pending_remove_operations.keys()):
                if now - self.pending_remove_operations[oid]["timestamp"] > self.ACTION_TIMEOUT:
                    self.pending_remove_operations.pop(oid, None)
                    self.high_confidence_frames[oid] = 0

            # Disappeared handling
            for oid in list(self.object_in_cart_state.keys()):
                if oid not in (detected_ids if boxes else set()):
                    self.disappeared_counter[oid] += 1
                    self.high_confidence_frames[oid] = max(0, self.high_confidence_frames[oid] - 1)
                    if self.object_in_cart_state[oid]:
                        self.cart_missing_counter[oid] += 1
                        if self.cart_missing_counter[oid] > self.MAX_MISSING_FRAMES_IN_ROI:
                            label = self.known_ids_in_cart.get(oid, "Unknown")
                            if self.products_in_cart[label] > 0:
                                self.products_in_cart[label] -= 1
                                self.total_removed[label] += 1
                            self.remove_from_cart(label, 1)
                            self._emit_detection("RA", label)
                            self.object_in_cart_state[oid] = False
                            self.cart_entry_time.pop(oid, None)
                            self.cart_missing_counter.pop(oid, None)
                    if self.disappeared_counter[oid] > self.MAX_MISSING_FRAMES:
                        self._forget_id(oid)

            self.msleep(10)

        self._debug("[INFO] YoloWorker stopped.")

    def stop(self):
        self.running = False
        self.wait()
        if hasattr(self, "cap") and self.cap is not None:
            try:
                self.cap.release()
            except Exception:
                pass
        try:
            cv2.destroyAllWindows()
        except Exception:
            pass
