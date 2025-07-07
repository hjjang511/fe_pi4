import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QStackedWidget
from views.map_page import MapPage
from views.shop_page import ShopPage
from views.cart_page import CartPage

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("Shopping App")
        self.setGeometry(100, 100, 1024, 768)

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        # Khởi tạo 3 page
        self.map_page = MapPage(self)
        self.shop_page = ShopPage(self)
        self.cart_page = CartPage(self)

        # Thêm vào stack
        self.stack.addWidget(self.map_page)
        self.stack.addWidget(self.shop_page)
        self.stack.addWidget(self.cart_page)

        self.stack.setCurrentWidget(self.map_page)

    def navigate_to(self, page_name):
        if page_name == "map":
            self.stack.setCurrentWidget(self.map_page)
        elif page_name == "shop":
            self.stack.setCurrentWidget(self.shop_page)
        elif page_name == "cart":
            self.stack.setCurrentWidget(self.cart_page)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
