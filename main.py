import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QStackedWidget
from views.map_page import MapPage
from views.shop_page import ShopPage
from views.cart_page import CartPage
from views.uart_worker import UartWorker
from views.waiting_page import WaitingPage
from views.payment_page import PaymentPage
# from views.yolo_worker import YoloWorker  # đảm bảo file yolo_worker.py chứa class YoloWorker
# from PyQt5.QtCore import QThread


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("Shopping App")
        self.setGeometry(100, 100, 1024, 768)

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        # Các page
        self.waiting_page = WaitingPage(self)
        self.shop_page = ShopPage(self)
        self.map_page = MapPage(self)
        self.cart_page = CartPage(self)
        self.payment_page = PaymentPage(self)
        self.stack.addWidget(self.payment_page)
        # Thêm vào stack
        self.stack.addWidget(self.waiting_page)
        self.stack.addWidget(self.map_page)
        self.stack.addWidget(self.shop_page)
        self.stack.addWidget(self.cart_page)

        # Bắt đầu ở Waiting Page
        self.stack.setCurrentWidget(self.waiting_page)

        # Khởi động UART worker
        self.uart_worker = UartWorker(port="COM9", baudrate=9600)
        self.uart_worker.data_received.connect(self.handle_uart_log)
        self.uart_worker.start()

    def navigate_to(self, page_name, **kwargs):
        if page_name == "waiting":
            self.stack.setCurrentWidget(self.waiting_page)
        elif page_name == "shop":
            self.stack.setCurrentWidget(self.shop_page)
        elif page_name == "map":
            self.stack.setCurrentWidget(self.map_page)
        elif page_name == "cart":
            self.stack.setCurrentWidget(self.cart_page)
        elif page_name == "payment":
            amount = kwargs.get("amount", None)
            if amount is not None:
                self.payment_page.set_amount(amount)
            self.stack.setCurrentWidget(self.payment_page)

    def handle_uart_log(self, text: str):
        # Parse log để điều hướng
        if "Heard on" in text:
            self.navigate_to("shop")
        elif "Heard off" in text:
            self.navigate_to("waiting")

    def closeEvent(self, event):
        self.uart_worker.stop()
        event.accept()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())