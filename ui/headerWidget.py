from PyQt5 import QtWidgets, QtGui, QtCore

class HeaderWidget(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(50, 0, 50, 0)
        layout.setSpacing(20)

        # Search section
        search_layout = QtWidgets.QHBoxLayout()
        search_layout.setSpacing(10)

        self.main_btn = QtWidgets.QPushButton()
        self.main_btn.setIcon(QtGui.QIcon("asset/img/main_icon.png"))
        self.main_btn.setIconSize(QtCore.QSize(34, 34))
        self.main_btn.setFlat(True)
        search_layout.addWidget(self.main_btn)

        self.search_line = QtWidgets.QLineEdit("Search")
        search_layout.addWidget(self.search_line)

        self.search_btn = QtWidgets.QPushButton()
        self.search_btn.setIcon(QtGui.QIcon("asset/img/search.png"))
        search_layout.addWidget(self.search_btn)

        layout.addLayout(search_layout)

        # Navigation buttons
        nav_layout = QtWidgets.QHBoxLayout()
        nav_layout.setSpacing(20)

        self.shop_btn = QtWidgets.QPushButton("Shop")
        nav_layout.addWidget(self.shop_btn)

        self.map_btn = QtWidgets.QPushButton("Map")
        self.map_btn.setCheckable(True)
        nav_layout.addWidget(self.map_btn)

        self.cart_btn = QtWidgets.QPushButton("Cart")
        nav_layout.addWidget(self.cart_btn)

        layout.addLayout(nav_layout)
