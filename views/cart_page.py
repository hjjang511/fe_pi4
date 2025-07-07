from PyQt5.QtWidgets import QWidget
from ui.cart_view import Ui_cart_view

class CartPage(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.ui = Ui_cart_view()
        self.ui.setupUi(self)
        self.main_window = main_window

        # Điều hướng
        self.ui.map_btn.clicked.connect(lambda: self.main_window.navigate_to("map"))
        self.ui.shop_btn.clicked.connect(lambda: self.main_window.navigate_to("shop"))

        # TODO: load sản phẩm đã thêm vào giỏ
