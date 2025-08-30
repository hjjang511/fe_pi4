import datetime
from PyQt5 import QtCore, QtGui, QtWidgets
import csv
import requests
import os
from dotenv import load_dotenv
# Load biến môi trường
load_dotenv()
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:5000/api")  # fallback localhost
class Ui_cart_view(object):
    def setupUi(self, Form):
        Form.setObjectName("cart_view")
        Form.resize(1024, 768)

        self.layout = QtWidgets.QVBoxLayout(Form)
        self.layout.setContentsMargins(0, 0, 0, 0)

        # Header
        self.header = QtWidgets.QHBoxLayout()
        self.header.setContentsMargins(50, 0, 50, 0)
        self.header.setSpacing(20)

        self.horizontalLayout_5 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_5.setSpacing(10)

        self.main_btn = QtWidgets.QPushButton()
        self.main_btn.setIcon(QtGui.QIcon("asset/img/main_icon.png"))
        self.main_btn.setIconSize(QtCore.QSize(34, 34))
        self.main_btn.setFlat(True)
        self.horizontalLayout_5.addWidget(self.main_btn)

        self.search_line = QtWidgets.QLineEdit()
        self.search_line.setText("Search")
        self.horizontalLayout_5.addWidget(self.search_line)

        self.search_btn = QtWidgets.QPushButton()
        self.search_btn.setIcon(QtGui.QIcon("asset/img/search.png"))
        self.horizontalLayout_5.addWidget(self.search_btn)

        self.header.addLayout(self.horizontalLayout_5)

        self.horizontalLayout_3 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_3.setSpacing(20)

        self.shop_btn = QtWidgets.QPushButton("Shop")
        self.horizontalLayout_3.addWidget(self.shop_btn)

        self.map_btn = QtWidgets.QPushButton("Map")
        self.map_btn.setCheckable(True)
        self.map_btn.setChecked(True)
        self.horizontalLayout_3.addWidget(self.map_btn)

        self.list_btn = QtWidgets.QPushButton("Cart")
        self.horizontalLayout_3.addWidget(self.list_btn)

        self.header.addLayout(self.horizontalLayout_3)
        self.layout.addLayout(self.header)

        # Main content
        self.main_group = QtWidgets.QGroupBox()
        self.main_group.setFixedSize(1000, 600)   
        self.main_layout = QtWidgets.QHBoxLayout(self.main_group)
        self.main_layout.setContentsMargins(50, 10, 50, 10)
        self.tableWidget = QtWidgets.QTableWidget()
        self.tableWidget.setColumnCount(7)
        self.tableWidget.setHorizontalHeaderLabels([
            "Index", "Name", "Description", "Price", "Quantity", "Discount", "Total"
        ])
        self.tableWidget.verticalHeader().setVisible(False)
        self.tableWidget.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.main_layout.addWidget(self.tableWidget)

        self.layout.addWidget(self.main_group)

        # Footer
        self.footer_widget = QtWidgets.QWidget()
        self.footer_layout = QtWidgets.QHBoxLayout(self.footer_widget)
        self.footer_layout.setContentsMargins(50, 0, 50, 0)

        self.cart_btn = QtWidgets.QPushButton()
        self.cart_btn.setIcon(QtGui.QIcon("asset/img/cart.png"))
        self.cart_btn.setIconSize(QtCore.QSize(34, 34))
        self.cart_btn.setFlat(True)

        self.cart_lb = QtWidgets.QLabel("0 Product")
        self.lb_mount = QtWidgets.QLabel("TOTAL MOUNT")
        self.amout_lb = QtWidgets.QLabel("0")

        self.footer_layout.addWidget(self.cart_btn)
        self.footer_layout.addWidget(self.cart_lb)
        self.footer_layout.addStretch()
        self.footer_layout.addWidget(self.lb_mount)
        self.footer_layout.addWidget(self.amout_lb)
        self.pay_btn = QtWidgets.QPushButton("Thanh Toán")
        self.pay_btn.setStyleSheet("padding: 8px 16px; font-weight: bold; background-color: #4CAF50; color: white;")
        self.footer_layout.addWidget(self.pay_btn)
        self.layout.addWidget(self.footer_widget)
        QtCore.QMetaObject.connectSlotsByName(Form)


    def load_cart_data(self, csv_file):
        with open(csv_file, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            data = list(reader)

        self.tableWidget.setRowCount(len(data))
        total_amount = 0

        for row, item in enumerate(data):
            price = float(item["price"])
            quantity = int(item["quantity"])
            discount = float(item["discount"])
            total = price * quantity * (1 - discount)
            total_amount += total

            self.tableWidget.setItem(row, 0, QtWidgets.QTableWidgetItem(item["index"]))
            self.tableWidget.setItem(row, 1, QtWidgets.QTableWidgetItem(item["name"]))
            self.tableWidget.setItem(row, 2, QtWidgets.QTableWidgetItem(item["description"]))
            self.tableWidget.setItem(row, 3, QtWidgets.QTableWidgetItem(f"${price:.2f}"))
            self.tableWidget.setItem(row, 4, QtWidgets.QTableWidgetItem(str(quantity)))
            self.tableWidget.setItem(row, 5, QtWidgets.QTableWidgetItem(f"{discount*100:.0f}%"))
            self.tableWidget.setItem(row, 6, QtWidgets.QTableWidgetItem(f"${total:.2f}"))

        self.cart_lb.setText(f"{len(data)} Product")
        self.amout_lb.setText(f"${total_amount:.2f}")
