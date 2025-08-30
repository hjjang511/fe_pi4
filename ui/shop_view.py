# -*- coding: utf-8 -*-
import requests
import csv
import os
from PyQt5.QtCore import Qt
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QLabel, QPushButton, QTableWidgetItem
from PyQt5.QtGui import QPixmap,QImage
from ui.map_view import Ui_map_view
from io import BytesIO
import os
from dotenv import load_dotenv
# Load biến môi trường
load_dotenv()
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:5000/api")
class Ui_shop_view(object):
    def setupUi(self, Form):
        Form.setObjectName("shop_view")
        Form.resize(1024, 768)

        self.layout = QtWidgets.QVBoxLayout(Form)
        self.layout.setContentsMargins(0, 0, 0, 0)

        # --- Header ---
        self.header = QtWidgets.QHBoxLayout()
        self.header.setContentsMargins(50, 0, 50, 0)
        self.header.setSpacing(20)

        self.header_left = QtWidgets.QHBoxLayout()
        self.header_left.setSpacing(10)

        self.main_btn = QtWidgets.QPushButton()
        self.main_btn.setIcon(QtGui.QIcon("asset/img/main_icon.png"))
        self.main_btn.setIconSize(QtCore.QSize(34, 34))
        self.main_btn.setFlat(True)
        self.header_left.addWidget(self.main_btn)

        self.search_line = QtWidgets.QLineEdit()
        self.search_line.setText("Search")
        self.header_left.addWidget(self.search_line)

        self.search_btn = QtWidgets.QPushButton()
        self.search_btn.setIcon(QtGui.QIcon("asset/img/search.png"))
        self.header_left.addWidget(self.search_btn)

        self.header.addLayout(self.header_left)

        self.header_right = QtWidgets.QHBoxLayout()
        self.header_right.setSpacing(20)

        self.shop_btn = QtWidgets.QPushButton("Shop")
        self.header_right.addWidget(self.shop_btn)

        self.map_btn = QtWidgets.QPushButton("Map")
        self.map_btn.setCheckable(True)
        self.map_btn.setChecked(True)
        self.header_right.addWidget(self.map_btn)

        self.list_btn = QtWidgets.QPushButton("Cart")
        self.header_right.addWidget(self.list_btn)

        self.header.addLayout(self.header_right)
        self.layout.addLayout(self.header)

        # --- Main Content ---
        self.main_group = QtWidgets.QGroupBox()
        self.main_group.setFixedSize(1000, 600)
        self.main_layout = QtWidgets.QHBoxLayout(self.main_group)
        self.main_layout.setContentsMargins(50, 10, 50, 10)
        
        self.tableWidget = QtWidgets.QTableWidget()
        self.tableWidget.setColumnCount(8)
        self.tableWidget.setHorizontalHeaderLabels([
            "Index", "Image", "Name", "Aisles", "Description", "Price", "Discount", "Add to List"
        ])
        self.tableWidget.verticalHeader().setVisible(False)
        self.tableWidget.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.main_layout.addWidget(self.tableWidget)

        self.layout.addWidget(self.main_group)

        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)
        
        self.load_shop_data()

        
    def add_to_list(self, item):
        list_file = "data/list_data.csv"

        # Kiểm tra xem đã có chưa
        existing = []
        try:
            with open(list_file, newline='') as csvfile:
                reader = csv.DictReader(csvfile)
                existing = [row["index"] for row in reader]
        except FileNotFoundError:
            pass  # File sẽ được tạo sau

        if item["id"] in existing:
            print(f"Sản phẩm {item['name']} đã có trong danh sách.")
            return

        # Thêm mới
        with open(list_file, "a", newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=[
                "id", "image", "name", "aisle", "description", "price", "discount"
            ])
            if os.stat(list_file).st_size == 0:  # Nếu file mới
                writer.writeheader()

            writer.writerow({
                "id": item["id"],
                "image": item["image"],
                "name": item["name"],
                "aisle": item["aisle"],
                "description": item["description"],
                "price": item["price"],
                "discount": item["discount"]
            })
        print(f"✅ Đã thêm: {item['name']}")

    def load_shop_data(self, api_url=None):
        base = API_BASE_URL.rstrip('/')
        if api_url is None:
            api_url = base + ("/products" if base.endswith("/api") else "/api/products")

        try:
            response = requests.get(api_url)
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            print(f"❌ Lỗi khi gọi API: {e}")
            return

        # === LƯU VÀO CSV NGAY TẠI ĐÂY ===
        self.save_shop_csv(data, "data/shop_data.csv")

        # === Phần hiển thị như cũ ===
        self.tableWidget.setRowCount(len(data))

        # Chuẩn hóa host cho ảnh tĩnh (tránh '/api/static')
        host = base[:-4] if base.endswith("/api") else base

        for row, item in enumerate(data):
            # Index
            self.tableWidget.setItem(row, 0, QTableWidgetItem(str(item["id"])))

            # Image
            image_label = QLabel()
            image_url = f"{host}/static/{item['image']}"
            try:
                img_res = requests.get(image_url)
                if img_res.status_code == 200:
                    image = QImage()
                    image.loadFromData(img_res.content)
                    pixmap = QPixmap(image).scaled(60, 60, QtCore.Qt.KeepAspectRatio)
                    image_label.setPixmap(pixmap)
                else:
                    print(f"⚠️ Không tải được ảnh từ {image_url}")
            except Exception as e:
                print(f"⚠️ Lỗi tải ảnh: {e}")
            self.tableWidget.setCellWidget(row, 1, image_label)

            # Name
            self.tableWidget.setItem(row, 2, QTableWidgetItem(item["name"]))
            # Aisle
            self.tableWidget.setItem(row, 3, QTableWidgetItem(item["aisle"]))
            # Description
            self.tableWidget.setItem(row, 4, QTableWidgetItem(item.get("description", "")))
            # Price
            self.tableWidget.setItem(row, 5, QTableWidgetItem(f"${float(item['price']):.2f}"))
            # Discount
            discount = float(item.get("discount", 0) or 0)
            self.tableWidget.setItem(row, 6, QTableWidgetItem(f"{discount*100:.0f}%"))

            # Add button (nếu vẫn muốn giữ)
            btn = QPushButton("Add")
            btn.setProperty("product_id", item["id"])
            btn.clicked.connect(lambda checked, item=item: self.add_to_list(item))
            self.tableWidget.setCellWidget(row, 7, btn)


    def save_shop_csv(self, items, csv_path="data/shop_data.csv"):
        os.makedirs(os.path.dirname(csv_path), exist_ok=True)
        fieldnames = ["id", "image", "name", "aisle", "description","quantity", "price", "discount"]
        with open(csv_path, "w", newline="", encoding="utf-8") as f:  # "w" = ghi đè mỗi lần fetch
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for it in items:
                writer.writerow({
                    "id": it.get("id"),
                    "image": it.get("image", ""),
                    "name": it.get("name", ""),
                    "aisle": it.get("aisle", ""),
                    "description": it.get("description", ""),
                    "quantity": it.get("quantity", 0),
                    "price": float(it.get("price", 0) or 0),
                    "discount": float(it.get("discount", 0) or 0),
                })

    def retranslateUi(self, Form):
        _translate = QtCore.QCoreApplication.translate
        Form.setWindowTitle(_translate("shop_view", "Shop View"))
        self.search_line.setPlaceholderText(_translate("shop_view", "Search products..."))
