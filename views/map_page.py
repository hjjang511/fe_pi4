# views/map_page.py
import asyncio
import csv
import datetime
from PyQt5.QtWidgets import QWidget, QVBoxLayout
from PyQt5.QtCore import QUrl, QTimer
from PyQt5.QtWebEngineWidgets import QWebEngineView
import joblib
from receive_ble import scan_once
from trilateration import rssi_to_distance, trilaterate
from kalman import KalmanFilter2D
from ui.map_view import Ui_map_view
import os

class MapPage(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.ui = Ui_map_view()
        self.ui.setupUi(self)
        self.main_window = main_window

        # Tạo trình duyệt map
        self.map_view = QWebEngineView()
        html_path = os.path.abspath("resource/map.html")
        self.map_view.load(QUrl.fromLocalFile(html_path))

        # Khởi tạo Kalman Filter
        self.kalman_filter = KalmanFilter2D()

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
        # Load mô hình
        self.model = joblib.load("model/ble_model.pkl")

        # Thiết lập timer để quét BLE mỗi 1 giây
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.scan_and_update_position)

        self.beacons_pos = {
            "0-0": (0, 0),
            "0-30": (0, 30),
            "15-30": (15, 30)
        }
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
        try:
            rssi_dict = asyncio.run(scan_once())
            print("RSSI:", rssi_dict)

            # ---- Dự đoán từ model ML ----
            input_vector = [rssi_dict.get("0-0", -100),
                            rssi_dict.get("0-30", -100),
                            rssi_dict.get("15-30", -100)]
            x_ml, y_ml = self.model.predict([input_vector])[0]

            # ---- Tính khoảng cách từ RSSI ----
            d1 = rssi_to_distance(rssi_dict["0-0"])
            d2 = rssi_to_distance(rssi_dict["0-30"])
            d3 = rssi_to_distance(rssi_dict["15-30"])

            # ---- Dự đoán từ trilateration ----
            x_tri, y_tri = trilaterate(self.beacons_pos["0-0"], d1,
                                        self.beacons_pos["0-30"], d2,
                                        self.beacons_pos["15-30"], d3)

            # ---- Trung bình 2 kết quả hoặc chọn kết quả tin cậy hơn ----
            x = (x_ml + x_tri) / 2
            y = (y_ml + y_tri) / 2

            print(f"ML: ({x_ml:.1f}, {y_ml:.1f}) | Trilateration: ({x_tri:.1f}, {y_tri:.1f}) → Combined: ({x:.1f}, {y:.1f})")
            # 🧠 Lọc Kalman
            self.kalman.predict()
            self.kalman.update([x, y])
            x_kf, y_kf = self.kalman.get_position()
            # ---- Cập nhật marker trên map ----
            self.map_view.page().runJavaScript(f"updateMarker({x_kf}, {y_kf})")
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.path_writer.writerow([timestamp, round(x_kf, 2), round(y_kf, 2)])
            self.path_log_file.flush()  # đảm bảo ghi ngay
        except Exception as e:
            print("❌ Lỗi dự đoán vị trí:", e)
            
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
        if hasattr(self, "data/path_log_file"):
            self.path_log_file.close()
        event.accept()