from PyQt5.QtWidgets import QWidget
from ui.cart_view import Ui_cart_view

class CartPage(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.ui = Ui_cart_view()
        self.ui.setupUi(self)

        # Truyền tham chiếu để Ui_cart_view có thể gọi navigate_to
        self.setParent(self.main_window)

        # Điều hướng nút bấm
        self.ui.map_btn.clicked.connect(lambda: self.main_window.navigate_to("map"))
        self.ui.shop_btn.clicked.connect(lambda: self.main_window.navigate_to("shop"))
        self.ui.list_btn.clicked.connect(lambda: self.main_window.navigate_to("cart"))
        self.ui.pay_btn.clicked.connect(self.goto_payment)

        # Dữ liệu giỏ hàng {label: quantity}
        self.cart_items = {}

    def goto_payment(self):
        total_amount = int(float(self.ui.amout_lb.text().replace("$", "")))
        self.main_window.navigate_to("payment", amount=total_amount)
