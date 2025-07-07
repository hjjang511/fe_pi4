from PyQt5.QtWidgets import QWidget
from ui.shop_view import Ui_shop_view

class ShopPage(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.ui = Ui_shop_view()
        self.ui.setupUi(self)
        self.main_window = main_window

        # Gán main_window cho Ui_shop_view để dùng trong add_to_list
        self.ui.main_window = main_window

        # Điều hướng
        self.ui.map_btn.clicked.connect(self.reload_map_list)
        self.ui.map_btn.clicked.connect(lambda: self.main_window.navigate_to("map"))
        self.ui.list_btn.clicked.connect(lambda: self.main_window.navigate_to("cart"))

    def reload_map_list(self):
        if hasattr(self, "main_window"):
            map_page = self.main_window.map_page 
            if map_page and hasattr(map_page, "ui"):
                map_page.ui.load_list_data("data/list_data.csv")
                map_page.ui.tableWidget.viewport().update()
                print("✅ Map page updated")

