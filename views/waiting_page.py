from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QPushButton
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt

class WaitingPage(QWidget):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window  # giữ tham chiếu tới MainWindow

        layout = QVBoxLayout(self)

        label = QLabel("WELCOME TO GoMarket")
        label.setFont(QFont("Arial", 48))
        label.setAlignment(Qt.AlignCenter)

        button = QPushButton("Start Shopping")
        button.clicked.connect(self.goto_shopping)

        # Thêm vào layout
        layout.addWidget(label)
        layout.addWidget(button)

        self.setLayout(layout)

    def goto_shopping(self):
        # gọi điều hướng sang trang shop
        self.main_window.navigate_to("shop")
