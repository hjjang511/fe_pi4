# views/map_page.py
import asyncio
import csv
import datetime
from PyQt5.QtWidgets import QWidget, QVBoxLayout
from PyQt5.QtCore import QUrl, QTimer
from PyQt5.QtWebEngineWidgets import QWebEngineView
import joblib
from views.yolo_worker import YoloWorker
from rssi_positon.rssi_filter import RSSIFilter
from rssi_positon.trilateration import rssi_to_distance, trilaterate
from rssi_positon.kalman import KalmanFilter2D
from ui.map_view import Ui_map_view
import os
import pandas as pd

from views.ble_worker import BLEScannerThread

class MapPage(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.ui = Ui_map_view()
        self.ui.setupUi(self)
        self.main_window = main_window

        # Tạo trình duyệt map
        self.map_view = QWebEngineView()

        self.map_view.load(QUrl.fromLocalFile(os.path.abspath("resource/map.html")))

        self.map_loaded = False
        self.map_view.loadFinished.connect(self.on_map_loaded)

        # Khởi tạo Kalman Filter
        self.kalman_filter = KalmanFilter2D()
        self.kalman_filter.set_position([1, 0])  
        self.last_pos = [1, 0]

        self.yolo_thread = YoloWorker("model/my_model.pt")
        self.yolo_thread.detection_result.connect(self.handle_yolo_result)
        self.ui.recognize_btn.toggled.connect(self.toggle_yolo)

        self.rssi_filter = RSSIFilter(window_size=7)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.map_view.setMinimumSize(500, 500)

        layout.addWidget(self.map_view)
        self.ui.map_container.setLayout(layout)

        # Kết nối nút điều hướng
        self.ui.shop_btn.clicked.connect(lambda: self.main_window.navigate_to("shop"))
        self.ui.list_btn.clicked.connect(lambda: self.main_window.navigate_to("cart"))

        # Kết nối nút chỉ đường
        self.ui.nagative_btn.clicked.connect(self.navigate_all_items)

        self.ui.scan_btn.toggled.connect(self.toggle_ble_scan)

        self.path_log_file = open("data/path_log.csv", "w", newline="")
        self.path_writer = csv.writer(self.path_log_file)
        self.path_writer.writerow(["timestamp", "x", "y"])
        self.ble_thread = BLEScannerThread()
        self.ble_thread.rssi_signal.connect(self.handle_ble_data)

        # Load mô hình
        self.model = joblib.load("model/ble_model_v2.pkl")

        # Thiết lập timer để quét BLE mỗi 1 giây
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.scan_and_update_position)

        self.beacons_pos = {
            "0-0": (6, 8),
            "0-30": (0, 8),
            "15-30": (0, 0)
        }
    def on_map_loaded(self, ok):
        if ok:
            print("? Map loaded th�nh c�ng")
            self.map_loaded = True
        else:
            print("? Map load th?t b?i")

    def toggle_ble_scan(self, checked):
        if checked:
            self.ui.scan_btn.setText("🔄 Scanning...")
            self.timer.start(1000)
            print("▶️ Bắt đầu quét BLE")
        else:
            self.ui.scan_btn.setText("▶️ Start Scan")
            self.timer.stop()
            print("⏸️ Dừng quét BLE")
            
    def scan_and_update_position(self):
        if not self.ble_thread.isRunning():
            self.ble_thread.start()

    def handle_ble_data(self, rssi_dict):
        try:
            print("RSSI raw:", rssi_dict)

            # --- 1. L?c RSSI ---
            filtered_rssi = {
                k: self.rssi_filter.update(k, v)
                for k, v in rssi_dict.items()
            }

            print("RSSI filtered:", filtered_rssi)

                # --- D? �o�n b?ng m� h?nh ML ---
            input_df = pd.DataFrame([{
                "0-0": filtered_rssi.get("0-0", -100),
                "0-30": filtered_rssi.get("0-30", -100),
                "15-30": filtered_rssi.get("15-30", -100)
            }])
            x_ml, y_ml = self.model.predict(input_df)[0]

            # --- B? trilateration ho�n to�n (n?u b?n ch�a d�ng t?t) ---
            x, y = x_ml, y_ml
            print(f"ML Position: ({x:.2f}, {y:.2f})")

            # --- 3. Kalman filter ---
            self.kalman_filter.predict()
            self.kalman_filter.update([x, y])
            x_kf, y_kf = self.kalman_filter.get_position()

            # --- 4. Gi?i h?n trong b?n �? ---
            x_kf = max(0, min(x_kf, 15))
            y_kf = max(0, min(y_kf, 30))

            # --- 5. Gi?i h?n nh?y nh? ---
            dx = abs(x_kf - self.last_pos[0])
            dy = abs(y_kf - self.last_pos[1])

            movement_threshold = 0.5  # Gi? nguy�n n?u g?n nh� �?ng y�n
            if dx < movement_threshold and dy < movement_threshold:
                print(f"?? �?ng y�n t?i ({self.last_pos[0]:.2f}, {self.last_pos[1]:.2f})")
                x_kf, y_kf = self.last_pos

            # --- 6. Gi?i h?n thay �?i qu� l?n ---
            delta_threshold = 1.5  # t?i �a 1.5 grid
            if dx < delta_threshold and dy < delta_threshold:
                if self.map_loaded:
                    pixel_x = x_kf * 15
                    pixel_y = y_kf * 15
                    self.map_view.page().runJavaScript(f"setStartPosition({pixel_x}, {pixel_y})")
                    self.map_view.page().runJavaScript(f"updateMarker({pixel_x}, {pixel_y})")   
                self.last_pos = [x_kf, y_kf]
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.path_writer.writerow([timestamp, round(x_kf, 2), round(y_kf, 2)])
                self.path_log_file.flush()
                print(f"? V? tr� c?p nh?t: ({x_kf:.2f}, {y_kf:.2f}) | dx={dx:.2f}, dy={dy:.2f}")
            else:
                print(f"?? B? qua c?p nh?t do nh?y qu� xa: ?x={dx:.2f}, ?y={dy:.2f}")

        except Exception as e:
            print("? L?i x? l? BLE:", e)


            
    def navigate_all_items(self):
        # Lấy danh sách kệ từ bảng sản phẩm
        aisle_list = []
        for row in range(self.ui.tableWidget.rowCount()):
            aisle_item = self.ui.tableWidget.item(row, 1)
            if aisle_item:
                aisle = aisle_item.text()
                if aisle and aisle not in aisle_list:
                    aisle_list.append(aisle)

        if aisle_list:
            js_array = str(aisle_list).replace("'", '"')  # Chuyển sang mảng JavaScript
            self.map_view.page().runJavaScript(f'navigateAll({js_array})')

    def closeEvent(self, event):
        if hasattr(self, "path_log_file"):
            self.path_log_file.close()
        event.accept()
        
    def toggle_yolo(self, checked):
        if checked:
            self.ui.recognize_btn.setText("🟢 Recognizing...")
            if not self.yolo_thread.isRunning():
                self.yolo_thread.start()
        else:
            self.ui.recognize_btn.setText("🔍 Recognize")
            if self.yolo_thread.isRunning():
                self.yolo_thread.stop()

    def handle_yolo_result(self, cls_name):
        print(f"✅ YOLO phát hiện: {cls_name}")
        # bạn có thể update UI hoặc gửi về backend ở đây
