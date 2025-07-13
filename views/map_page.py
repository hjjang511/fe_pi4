# views/map_page.py
import asyncio
import csv
import datetime
from PyQt5.QtWidgets import QWidget, QVBoxLayout
from PyQt5.QtCore import QUrl, QTimer
from PyQt5.QtWebEngineWidgets import QWebEngineView
import joblib
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
            print("RSSI:", rssi_dict)

            input_df = pd.DataFrame([{
                "0-0": rssi_dict.get("0-0", -100),
                "0-30": rssi_dict.get("0-30", -100),
                "15-30": rssi_dict.get("15-30", -100)
            }])
            print("Input to ML:", input_df.to_dict(orient='records'))
            x_ml, y_ml = self.model.predict(input_df)[0]

            d1 = rssi_to_distance(rssi_dict["0-0"])
            d2 = rssi_to_distance(rssi_dict["0-30"])
            d3 = rssi_to_distance(rssi_dict["15-30"])

            x_tri, y_tri = trilaterate(self.beacons_pos["0-0"], d1,
                                    self.beacons_pos["0-30"], d2,
                                    self.beacons_pos["15-30"], d3)

            x = x_ml*1 + x_tri*0
            y = y_ml*1 + y_tri*0
            
            print(f"ML: ({x_ml:.1f}, {y_ml:.1f}) | Trilateration: ({x_tri:.1f}, {y_tri:.1f}) ? Combined: ({x:.1f}, {y:.1f})")

            self.kalman_filter.predict()
            self.kalman_filter.update([x, y])
            x_kf, y_kf = self.kalman_filter.get_position()
            print(f"KF: ({x_kf:.1f},{y_kf:.1f})")
            # �o?n cu?i trong handle_ble_data
            scale = 15
            dx = abs(x_kf - self.last_pos[0])
            dy = abs(y_kf - self.last_pos[1])
            delta_threshold = 2  # t?i �a 3 grid

            if dx < delta_threshold and dy < delta_threshold:
                if self.map_loaded:
                    self.map_view.page().runJavaScript(f"updateMarker({x_kf*scale}, {y_kf*scale})")
                self.last_pos = [x_kf, y_kf]
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.path_writer.writerow([timestamp, round(x_kf, 2), round(y_kf, 2)])
                self.path_log_file.flush()
            else:
                print(f"?? B? qua c?p nh?t do nh?y qu� xa: ?x={dx:.1f}, ?y={dy:.1f}")
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
