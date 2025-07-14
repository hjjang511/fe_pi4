# views/map_page.py
import asyncio
import csv
import datetime
from PyQt5.QtWidgets import QWidget, QVBoxLayout
from PyQt5.QtCore import QUrl, QTimer
from PyQt5.QtWebEngineWidgets import QWebEngineView
import joblib
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

        self.map_view.load(QUrl("http://192.168.0.103:5000/map"))

        self.map_loaded = False
        self.map_view.loadFinished.connect(self.on_map_loaded)

        # Khởi tạo Kalman Filter
        self.kalman_filter = KalmanFilter2D()
        self.kalman_filter.set_position([1, 0])  # V? 15 / 15 = 1, 0 / 15 = 0
        self.last_pos = [1, 0]

        self.rssi_filter = RSSIFilter(window_size=5)

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
            "0-0": (0, 0),
            "0-30": (0, 30),
            "15-30": (15, 30)
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

            # --- 1. Lọc RSSI ---
            filtered_rssi = {
                k: self.rssi_filter.update(k, v)
                for k, v in rssi_dict.items()
            }

            print("RSSI filtered:", filtered_rssi)

            # --- 2. Dự đoán vị trí bằng ML ---
            input_df = pd.DataFrame([{
                "0-0": filtered_rssi.get("0-0", -100),
                "0-30": filtered_rssi.get("0-30", -100),
                "15-30": filtered_rssi.get("15-30", -100)
            }])
            x_ml, y_ml = self.model.predict(input_df)[0]

            # --- 3. Tính khoảng cách và trilateration ---
            d1 = rssi_to_distance(filtered_rssi["0-0"])
            d2 = rssi_to_distance(filtered_rssi["0-30"])
            d3 = rssi_to_distance(filtered_rssi["15-30"])

            x_tri, y_tri = trilaterate(self.beacons_pos["0-0"], d1,
                                    self.beacons_pos["0-30"], d2,
                                    self.beacons_pos["15-30"], d3)

            # --- 4. Kết hợp ML và trilateration ---
            x = x_ml * 1 + x_tri * 0
            y = y_ml * 1 + y_tri * 0

            print(f"ML: ({x_ml:.1f}, {y_ml:.1f}) | Trilateration: ({x_tri:.1f}, {y_tri:.1f}) → Combined: ({x:.1f}, {y:.1f})")

            # --- 5. Kalman filter ---
            self.kalman_filter.predict()
            self.kalman_filter.update([x, y])
            x_kf, y_kf = self.kalman_filter.get_position()

            # --- 6. Giới hạn trong bản đồ ---
            x_kf = max(0, min(x_kf, 15))
            y_kf = max(0, min(y_kf, 30))

            # --- 7. Giữ nguyên nếu đứng yên ---
            dx = abs(x_kf - self.last_pos[0])
            dy = abs(y_kf - self.last_pos[1])
            movement_threshold = 0.1  # coi như đứng yên nếu nhỏ hơn

            if dx < movement_threshold and dy < movement_threshold:
                x_kf, y_kf = self.last_pos

            print(f"KF: ({x_kf:.2f},{y_kf:.2f})")

            # --- 8. Giới hạn thay đổi quá lớn ---
            delta_threshold = 2  # tối đa 2 grid (~30cm nếu scale=15)
            dx_vis = abs(x_kf - self.last_pos[0])
            dy_vis = abs(y_kf - self.last_pos[1])

            if dx_vis < delta_threshold and dy_vis < delta_threshold:
                if self.map_loaded:
                    self.map_view.page().runJavaScript(f"updateMarker({x_kf * 15}, {y_kf * 15})")
                self.last_pos = [x_kf, y_kf]
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.path_writer.writerow([timestamp, round(x_kf, 2), round(y_kf, 2)])
                self.path_log_file.flush()
            else:
                print(f"⚠️ Bỏ qua do nhảy quá xa: Δx={dx_vis:.2f}, Δy={dy_vis:.2f}")

        except Exception as e:
            print("❌ Lỗi xử lý BLE:", e)



            
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
