from PyQt5 import QtCore, QtGui, QtWidgets
import csv

class Ui_map_view(object):
    def setupUi(self, map_view):
        map_view.setObjectName("map_view")
        map_view.resize(1024, 768)

        # Layout chính dọc
        self.verticalLayout = QtWidgets.QVBoxLayout(map_view)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)

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
        self.verticalLayout.addLayout(self.header)

        # ---------------- MAIN CONTENT ----------------
        self.main_group = QtWidgets.QGroupBox()
        self.main_group.setTitle("")
        self.main_layout = QtWidgets.QHBoxLayout(self.main_group)
        self.main_layout.setContentsMargins(50, 10, 50, 10)
        # Map container (bản đồ ở giữa)
        self.map_container = QtWidgets.QWidget()
        self.map_container.setMaximumSize(450, 450)
        self.map_container.setSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Maximum)
        self.main_layout.addWidget(self.map_container)

        # Bảng phải
        self.right_box = QtWidgets.QGroupBox()
        self.right_box.setTitle("")
        self.right_box.setMaximumSize(444, 70000)
        self.right_box.setSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Maximum)

        self.right_layout = QtWidgets.QVBoxLayout(self.right_box)
        self.right_layout.setContentsMargins(20, 20, 20, 20)
        self.tableWidget = QtWidgets.QTableWidget()
        self.tableWidget.setMaximumHeight(600)
        self.tableWidget.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.tableWidget.setColumnCount(4)
        self.tableWidget.setHorizontalHeaderLabels(["Name", "Aisles", "Price", "Cancel"])
        self.tableWidget.horizontalHeader().setDefaultSectionSize(100)

        self.nagative_btn = QtWidgets.QPushButton("Nagative")
        self.scan_btn = QtWidgets.QPushButton("▶️ Start Scan")
        self.scan_btn.setCheckable(True)

        self.right_layout.addWidget(self.tableWidget)
        self.right_layout.addWidget(self.nagative_btn, alignment=QtCore.Qt.AlignHCenter)
        self.right_layout.addWidget(self.scan_btn, alignment=QtCore.Qt.AlignHCenter)

        self.main_layout.addWidget(self.right_box)
        self.verticalLayout.addWidget(self.main_group)

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

        self.verticalLayout.addWidget(self.footer_widget)


    def load_cart_data(self, file_path):
        try:
            with open(file_path, newline='') as csvfile:
                reader = csv.DictReader(csvfile)
                data = list(reader)
        except Exception as e:
            print(f"Error loading cart data: {e}")
            return

        self.tableWidget.setRowCount(len(data))
        total_price = 0
        for row_idx, row in enumerate(data):
            try:
                name = row["name"]
                aisle = row["aisle"]
                price = float(row["price"])
                quantity = int(row["quantity"])
                discount = float(row["discount"])
                final_price = price * quantity * (1 - discount)
                total_price += final_price

                self.tableWidget.setItem(row_idx, 0, QtWidgets.QTableWidgetItem(name))
                self.tableWidget.setItem(row_idx, 1, QtWidgets.QTableWidgetItem(aisle))
                self.tableWidget.setItem(row_idx, 2, QtWidgets.QTableWidgetItem(f"${final_price:.2f}"))

                cancel_btn = QtWidgets.QPushButton("❌")
                cancel_btn.clicked.connect(lambda _, r=row_idx: self.remove_row(r))
                self.tableWidget.setCellWidget(row_idx, 3, cancel_btn)
            except Exception as e:
                print(f"Error in cart row {row_idx}: {e}")

        self.cart_lb.setText(f"{len(data)} Product")
        self.amout_lb.setText(f"${total_price:.2f}")

    def load_list_data(self, file_path):
        self.tableWidget.setRowCount(0)
        try:
            with open(file_path, newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                data = list(reader)
        except Exception as e:
            print(f"❌ Error loading list data: {e}")
            return

        for row_idx, row in enumerate(data):
            try:
                name = row.get("name", "").strip()
                aisle = row.get("aisle", "").strip()
                price = float(row.get("price", 0))
                discount = float(row.get("discount", 0))
                final_price = price * (1 - discount)

                name_item = QtWidgets.QTableWidgetItem(name)
                aisle_item = QtWidgets.QTableWidgetItem(aisle)
                price_item = QtWidgets.QTableWidgetItem(f"${final_price:.2f}")

                self.tableWidget.insertRow(row_idx)
                self.tableWidget.setItem(row_idx, 0, name_item)
                self.tableWidget.setItem(row_idx, 1, aisle_item)
                self.tableWidget.setItem(row_idx, 2, price_item)

                cancel_btn = QtWidgets.QPushButton("❌")
                cancel_btn.clicked.connect(lambda _, r=row_idx: self.remove_row(r))
                self.tableWidget.setCellWidget(row_idx, 3, cancel_btn)
            except Exception as e:
                print(f"⚠️ Error processing row {row_idx}: {e}")


    def remove_row(self, row):
        # Xóa khỏi table
        self.tableWidget.removeRow(row)

        # Đọc lại toàn bộ dữ liệu từ file
        file_path = "data/list_data.csv"
        try:
            with open(file_path, newline='', encoding='utf-8') as csvfile:
                reader = list(csv.DictReader(csvfile))
                fieldnames = reader[0].keys() if reader else []
        except Exception as e:
            print(f"❌ Lỗi đọc file: {e}")
            return

        # Xóa dòng tương ứng
        if 0 <= row < len(reader):
            del reader[row]

            # Ghi lại file CSV mới (overwrite)
            try:
                with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(reader)
                print(f"✅ Đã xóa dòng {row} khỏi file CSV")
            except Exception as e:
                print(f"❌ Lỗi ghi lại file: {e}")



# Test chạy độc lập
if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    widget = QtWidgets.QWidget()
    ui = Ui_map_view()
    ui.setupUi(widget)
    widget.show()
    sys.exit(app.exec_())
