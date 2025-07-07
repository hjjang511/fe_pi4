from PyQt5 import QtWidgets, QtGui, QtCore

class FooterWidget(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(50, 0, 50, 0)

        self.cart_icon_btn = QtWidgets.QPushButton()
        self.cart_icon_btn.setIcon(QtGui.QIcon("asset/img/cart.png"))
        self.cart_icon_btn.setIconSize(QtCore.QSize(34, 34))
        self.cart_icon_btn.setFlat(True)

        self.cart_lb = QtWidgets.QLabel("0 Product")
        self.lb_mount = QtWidgets.QLabel("TOTAL MOUNT")
        self.amout_lb = QtWidgets.QLabel("0")

        layout.addWidget(self.cart_icon_btn)
        layout.addWidget(self.cart_lb)
        layout.addStretch()
        layout.addWidget(self.lb_mount)
        layout.addWidget(self.amout_lb)
