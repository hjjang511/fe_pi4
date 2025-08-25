import csv
import sys
import uuid
import hmac
import hashlib
import datetime
import requests

from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton
from PyQt5.QtCore import QTimer, QUrl
from PyQt5.QtGui import QDesktopServices
import os
from dotenv import load_dotenv
# Load biến môi trường
load_dotenv()
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:5000/api")

# === Config MoMo Test ===
PARTNER_CODE = "MOMO"
ACCESS_KEY = "F8BBA842ECF85"
SECRET_KEY = "K951B6PE1waDMi640xX08PD3vg6EkVlz"
MOMO_CREATE_URL = "https://test-payment.momo.vn/v2/gateway/api/create"
MOMO_QUERY_URL = "https://test-payment.momo.vn/v2/gateway/api/query"

REDIRECT_URL = "http://localhost:5000/payment/redirect"
IPN_URL = "http://localhost:5000/payment/ipn"

class PaymentPage(QWidget):
    def __init__(self, main_window, amount=100000):
        super().__init__()
        self.main_window = main_window
        self.amount = amount
        self.order_id = None
        self.request_id = None
        self.timer = None

        # Layout
        layout = QVBoxLayout()
        
        # WebView nhúng trang thanh toán MoMo
        self.webview = QWebEngineView()

        # Label hiển thị tổng tiền
        self.amount_label = QLabel(f"Tổng tiền: {self.amount} VND")

        # Label trạng thái
        self.status_label = QLabel("💳 Nhấn để thanh toán bằng MoMo")
        layout.addWidget(self.status_label)

        # Nút thanh toán
        pay_btn = QPushButton("Thanh toán MoMo")
        pay_btn.clicked.connect(self.handle_payment)
        layout.addWidget(self.amount_label)
        layout.addWidget(self.status_label)
        layout.addWidget(pay_btn)
        layout.addWidget(self.webview, stretch=1)  # WebView chiếm hết phần còn lại
        self.setLayout(layout)

    def set_amount(self, amount):
        self.amount = amount
        self.amount_label.setText(f"Tổng tiền: {amount} VND")
    
    # --- Step 1: Create payment ---
    def handle_payment(self):
        self.order_id = f"ORD-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
        self.request_id = str(uuid.uuid4())

        params = {
            "partnerCode": PARTNER_CODE,
            "accessKey": ACCESS_KEY,
            "requestId": self.request_id,
            "amount": str(self.amount),
            "orderId": self.order_id,
            "orderInfo": "Thanh toán giỏ hàng GoMarket",
            "redirectUrl": REDIRECT_URL,
            "ipnUrl": IPN_URL,
            "extraData": "",
            "requestType": "captureWallet",
            "lang": "vi"
        }

        params["signature"] = generate_signature_create(params)

        try:
            res = requests.post(MOMO_CREATE_URL, json=params)
            if res.status_code == 200:
                data = res.json()
                pay_url = data.get("payUrl")
                if pay_url:
                    self.webview.load(QUrl(pay_url))
                    self.status_label.setText("🔄 Đang chờ thanh toán MoMo...")
                    self.start_check_payment_status()
                else:
                    self.status_label.setText("❌ Không lấy được payUrl")
            else:
                self.status_label.setText(f"❌ Lỗi API tạo thanh toán: {res.text}")
        except Exception as e:
            self.status_label.setText(f"❌ Exception: {e}")

    # --- Step 2: Polling check ---
    def start_check_payment_status(self):
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_payment_status)
        self.timer.start(5000)

    def check_payment_status(self):
        params = {
            "partnerCode": PARTNER_CODE,
            "accessKey": ACCESS_KEY,
            "requestId": self.request_id,
            "orderId": self.order_id,
            "lang": "vi"
        }
        params["signature"] = generate_signature_query(params)

        try:
            res = requests.post(MOMO_QUERY_URL, json=params)
            if res.status_code == 200:
                data = res.json()
                result_code = data.get("resultCode")
                if result_code == 0:  # success
                    self.status_label.setText("✅ Thanh toán thành công!")
                    self.timer.stop()
                    self.send_payment_to_server()
                    self.main_window.navigate_to("waiting")
                elif result_code != 1000:  # not pending
                    self.status_label.setText(f"❌ Thanh toán thất bại: {result_code}")
                    self.timer.stop()
            else:
                self.status_label.setText(f"❌ Lỗi query: {res.text}")
        except Exception as e:
            self.status_label.setText(f"❌ Exception khi query: {e}")

    def send_payment_to_server(self):
        cart = []

        # ==== Đọc giỏ hàng từ cart.csv ====
        try:
            with open("data/cart_data.csv", newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    cart.append({
                        "index": row["id"],
                        "name": row["name"],
                        "price": float(row["price"]),
                        "quantity": int(row["quantity"]),
                        "total": float(row["total"])
                    })
        except Exception as e:
            print(f"❌ Lỗi đọc cart.csv: {e}")

        # ==== Đọc đường đi từ path_log.csv ====
        path_log = []
        try:
            with open("data/path_log.csv", newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    path_log.append({
                        "timestamp": row["timestamp"],
                        "x": float(row["x"]),
                        "y": float(row["y"])
                    })
        except Exception as e:
            print(f"❌ Lỗi đọc path_log.csv: {e}")

        if not cart:
            print("❗ Giỏ hàng rỗng, không gửi!")
            return

        # ==== Dữ liệu order ====
        order_data = {
            "timestamp": datetime.datetime.now().isoformat(),
            "cart": cart,
            "total_amount": sum(item["total"] for item in cart),
            "status": "PAID",
        }

        # ==== Dữ liệu path ====
        path_data = {"orderId": self.order_id, "path": path_log}

        # ==== Gửi đơn hàng ====
        try:
            response = requests.post(f"{API_BASE_URL}/api/orders", json=order_data)
            if response.status_code in [200, 201]:
                print("✅ Gửi đơn hàng thành công!")
            else:
                print(f"❌ Gửi đơn hàng thất bại: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"❌ Lỗi gửi order đến server: {e}")

        # ==== Gửi log_path ====
        if path_log:
            try:
                response = requests.post(f"{API_BASE_URL}/api/log_paths", json=path_data)
                if response.status_code in [200, 201]:
                    print("✅ Gửi log_path thành công!")
                else:
                    print(f"❌ Gửi log_path thất bại: {response.status_code} - {response.text}")
            except Exception as e:
                print(f"❌ Lỗi gửi path đến server: {e}")

def generate_signature_create(params: dict) -> str:
    raw_signature = (
        f"accessKey={params['accessKey']}"
        f"&amount={params['amount']}"
        f"&extraData={params['extraData']}"
        f"&ipnUrl={params['ipnUrl']}"
        f"&orderId={params['orderId']}"
        f"&orderInfo={params['orderInfo']}"
        f"&partnerCode={params['partnerCode']}"
        f"&redirectUrl={params['redirectUrl']}"
        f"&requestId={params['requestId']}"
        f"&requestType={params['requestType']}"
    )
    return hmac.new(
        SECRET_KEY.encode("utf-8"),
        raw_signature.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()


def generate_signature_query(params: dict) -> str:
    raw_signature = (
        f"accessKey={params['accessKey']}"
        f"&orderId={params['orderId']}"
        f"&partnerCode={params['partnerCode']}"
        f"&requestId={params['requestId']}"
    )
    return hmac.new(
        SECRET_KEY.encode("utf-8"),
        raw_signature.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()