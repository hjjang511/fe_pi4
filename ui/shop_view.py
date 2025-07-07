# -*- coding: utf-8 -*-

import csv
import os
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QLabel, QPushButton, QTableWidgetItem
from PyQt5.QtGui import QPixmap
from ui.map_view import Ui_map_view

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
        self.main_layout = QtWidgets.QHBoxLayout(self.main_group)

        self.tableWidget = QtWidgets.QTableWidget()
        self.tableWidget.setColumnCount(8)
        self.tableWidget.setHorizontalHeaderLabels([
            "Index", "Image", "Name", "Aisles", "Description", "Price", "Discount", "Add to List"
        ])
        self.tableWidget.verticalHeader().setVisible(False)
        self.tableWidget.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.main_layout.addWidget(self.tableWidget)

        self.layout.addWidget(self.main_group)

        # --- Footer ---
        self.footer_widget = QtWidgets.QWidget()
        self.footer_layout = QtWidgets.QHBoxLayout(self.footer_widget)
        self.footer_layout.setContentsMargins(50, 0, 50, 0)

        self.cart_icon_btn = QtWidgets.QPushButton()
        self.cart_icon_btn.setIcon(QtGui.QIcon("asset/img/cart.png"))
        self.cart_icon_btn.setIconSize(QtCore.QSize(34, 34))
        self.cart_icon_btn.setFlat(True)

        self.cart_lb = QtWidgets.QLabel("0 Product")
        self.lb_mount = QtWidgets.QLabel("TOTAL MOUNT")
        self.amout_lb = QtWidgets.QLabel("0")

        self.footer_layout.addWidget(self.cart_icon_btn)
        self.footer_layout.addWidget(self.cart_lb)
        self.footer_layout.addStretch()
        self.footer_layout.addWidget(self.lb_mount)
        self.footer_layout.addWidget(self.amout_lb)

        self.layout.addWidget(self.footer_widget)

        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)

        self.load_shop_data("data/shop_data.csv")

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

        if item["index"] in existing:
            print(f"Sản phẩm {item['name']} đã có trong danh sách.")
            return

        # Thêm mới
        with open(list_file, "a", newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=[
                "index", "image", "name", "aisle", "description", "price", "discount"
            ])
            if os.stat(list_file).st_size == 0:  # Nếu file mới
                writer.writeheader()

            writer.writerow({
                "index": item["index"],
                "image": item["image"],
                "name": item["name"],
                "aisle": item["aisle"],
                "description": item["description"],
                "price": item["price"],
                "discount": item["discount"]
            })
        print(f"✅ Đã thêm: {item['name']}")

    def load_shop_data(self, file_path):
        with open(file_path, newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            data = list(reader)
            self.tableWidget.setRowCount(len(data))

            for row, item in enumerate(data):
                # Index
                self.tableWidget.setItem(row, 0, QTableWidgetItem(str(item["index"])))

                # Image
                image_label = QLabel()
                pixmap = QPixmap(item["image"])
                pixmap = pixmap.scaled(60, 60, QtCore.Qt.KeepAspectRatio)
                image_label.setPixmap(pixmap)
                self.tableWidget.setCellWidget(row, 1, image_label)

                # Name
                self.tableWidget.setItem(row, 2, QTableWidgetItem(item["name"]))

                # Aisles
                self.tableWidget.setItem(row, 3, QTableWidgetItem(item["aisle"]))

                # Description
                self.tableWidget.setItem(row, 4, QTableWidgetItem(item["description"]))

                # Price
                self.tableWidget.setItem(row, 5, QTableWidgetItem(f"${float(item['price']):.2f}"))

                # Discount
                discount = float(item['discount'])
                self.tableWidget.setItem(row, 6, QTableWidgetItem(f"{discount*100:.0f}%"))

                # Add to List button
                btn = QPushButton("Add")
                btn.setProperty("product_id", item["index"])  # gắn id nếu cần xử lý sau
                btn.clicked.connect(lambda checked, item=item: self.add_to_list(item))
                self.tableWidget.setCellWidget(row, 7, btn)

    def retranslateUi(self, Form):
        _translate = QtCore.QCoreApplication.translate
        Form.setWindowTitle(_translate("shop_view", "Shop View"))
        self.search_line.setPlaceholderText(_translate("shop_view", "Search products..."))
