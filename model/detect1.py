import cv2
from ultralytics import YOLO
from collections import defaultdict, deque
import numpy as np
import time
import csv
from datetime import datetime

# === Cấu hình ===
MODEL_PATH = "my_model.pt"
SOURCE = 0
RESOLUTION = (640, 480)
ROI_BOX =(107, 0, 533, 480) # Vùng giỏ hàng

# === Cấu hình Action Detection ===
MIN_CONFIDENCE = 0.7              # Ngưỡng confidence tối thiểu để nhận diện
HIGH_CONFIDENCE = 0.9            # Ngưỡng confidence cao để xác nhận thao tác
TRAJECTORY_HISTORY = 10           # Số frame lưu lịch sử di chuyển
MIN_MOVEMENT_THRESHOLD = 20       # Ngưỡng di chuyển tối thiểu (pixels)
ACTION_CONFIRM_FRAMES = 3         # Số frame để xác nhận action
VERTICAL_WEIGHT = 1.5             # Trọng số cho chuyển động dọc (quan trọng hơn cho action vào/ra)

start_x, start_y = 10, 20

# === CSV Logging Configuration ===
CSV_FILE = f"cart_quantities_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

# === Khởi tạo model và camera ===
model = YOLO(MODEL_PATH)
cap = cv2.VideoCapture(SOURCE)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, RESOLUTION[0])
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, RESOLUTION[1])

# === Biến theo dõi cho Smart Cart ===
total_vao = defaultdict(int)              # Tổng số lần cho vào giỏ
total_ra = defaultdict(int)               # Tổng số lần lấy ra khỏi giỏ
object_trajectories = defaultdict(lambda: deque(maxlen=TRAJECTORY_HISTORY))
object_labels = {}
last_action_time = defaultdict(float)    # Thời gian action cuối cùng để tránh duplicate
action_cooldown = 1.0                     # Cooldown 1 giây giữa các action của cùng 1 object

# === Biến theo dõi confidence và action ===
confidence_history = defaultdict(lambda: deque(maxlen=5))
pending_actions = defaultdict(dict)       # Actions đang chờ xác nhận
action_confirm_counter = defaultdict(int) # Đếm số frame xác nhận action

log_history = deque(maxlen=30)
log_records_vao = []
log_records_ra = []

def init_csv_file():
    """Khởi tạo file CSV với headers"""
    with open(CSV_FILE, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['product', 'quantity']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
    
    print(f"📊 CSV file initialized: {CSV_FILE}")

def update_csv_quantities():
    """Cập nhật số lượng sản phẩm vào CSV"""
    all_labels = set(list(total_vao.keys()) + list(total_ra.keys()))
    
    with open(CSV_FILE, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['product', 'quantity']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for label in sorted(all_labels):
            vao = total_vao[label]
            ra = total_ra[label]
            current_quantity = max(0, vao - ra)  # Đảm bảo không âm
            
            writer.writerow({
                'product': label,
                'quantity': current_quantity
            })

def calculate_movement_vector(trajectory):
    """Tính vector chuyển động từ trajectory"""
    if len(trajectory) < 2:
        return None, None
    
    # Lấy điểm đầu và cuối của trajectory
    start_point = trajectory[0]
    end_point = trajectory[-1]
    
    dx = end_point[0] - start_point[0]
    dy = end_point[1] - start_point[1]
    
    return dx, dy

def detect_action(obj_id, trajectory, roi_box):
    """
    Phát hiện action dựa trên trajectory
    Returns: 'VAO', 'RA', hoặc None
    """
    if len(trajectory) < TRAJECTORY_HISTORY // 2:
        return None
    
    dx, dy = calculate_movement_vector(trajectory)
    if dx is None or dy is None:
        return None
    
    # Tính khoảng cách di chuyển với trọng số cho chuyển động dọc
    movement_distance = np.sqrt(dx**2 + (dy * VERTICAL_WEIGHT)**2)
    
    if movement_distance < MIN_MOVEMENT_THRESHOLD:
        return None
    
    roi_x1, roi_y1, roi_x2, roi_y2 = roi_box
    roi_center_y = (roi_y1 + roi_y2) / 2
    
    # Lấy các điểm để phân tích
    start_point = trajectory[0]
    end_point = trajectory[-1]
    mid_point = trajectory[len(trajectory)//2]
    
    # Kiểm tra action VAO (từ ngoài vào trong)
    # Object di chuyển từ trên xuống dưới VÀ từ ngoài vào trong ROI
    if dy > 0:  # Di chuyển xuống
        # Kiểm tra điểm đầu ở ngoài hoặc ở biên trên của ROI
        start_outside_or_top = (start_point[1] < roi_center_y or 
                                start_point[0] < roi_x1 or start_point[0] > roi_x2)
        # Kiểm tra điểm cuối ở trong ROI
        end_inside = (roi_x1 <= end_point[0] <= roi_x2 and 
                     roi_y1 <= end_point[1] <= roi_y2)
        
        if start_outside_or_top and end_inside:
            return 'VAO'
    
    # Kiểm tra action RA (từ trong ra ngoài)
    # Object di chuyển từ dưới lên trên VÀ từ trong ra ngoài ROI
    if dy < 0:  # Di chuyển lên
        # Kiểm tra điểm đầu ở trong ROI
        start_inside = (roi_x1 <= start_point[0] <= roi_x2 and 
                       roi_y1 <= start_point[1] <= roi_y2)
        # Kiểm tra điểm cuối ở ngoài hoặc ở biên trên của ROI
        end_outside_or_top = (end_point[1] < roi_center_y or 
                             end_point[0] < roi_x1 or end_point[0] > roi_x2)
        
        if start_inside and end_outside_or_top:
            return 'RA'
    
    # Kiểm tra chuyển động ngang mạnh (có thể là action VAO/RA từ bên cạnh)
    if abs(dx) > abs(dy) * 1.5:  # Chuyển động ngang là chủ yếu
        # Từ ngoài vào trong theo chiều ngang
        start_outside_horizontal = (start_point[0] < roi_x1 or start_point[0] > roi_x2)
        end_inside = (roi_x1 <= end_point[0] <= roi_x2 and 
                     roi_y1 <= end_point[1] <= roi_y2)
        
        if start_outside_horizontal and end_inside:
            return 'VAO'
        
        # Từ trong ra ngoài theo chiều ngang
        start_inside = (roi_x1 <= start_point[0] <= roi_x2 and 
                       roi_y1 <= start_point[1] <= roi_y2)
        end_outside_horizontal = (end_point[0] < roi_x1 or end_point[0] > roi_x2)
        
        if start_inside and end_outside_horizontal:
            return 'RA'
    
    return None

def get_avg_confidence(obj_id):
    """Tính confidence trung bình cho object"""
    if obj_id in confidence_history and len(confidence_history[obj_id]) > 0:
        return sum(confidence_history[obj_id]) / len(confidence_history[obj_id])
    return 0.0

# === Khởi tạo CSV file ===
init_csv_file()

# === Vòng lặp chính ===
frame_count = 0
start_time = time.time()

while True:
    ret, frame = cap.read()
    if not ret:
        break
    
    frame_count += 1
    current_time = time.time()
    results = model.track(frame, persist=True, verbose=False)
    boxes = results[0].boxes

    if not boxes or boxes.id is None or boxes.id.numel() == 0:
        detected_ids = set()
    else:
        ids = boxes.id.cpu().numpy().astype(int)
        boxes_xyxy = boxes.xyxy.cpu().numpy()
        classes = boxes.cls.cpu().numpy().astype(int)
        confidences = boxes.conf.cpu().numpy()
        detected_ids = set(ids)

        for i, obj_id in enumerate(ids):
            x1, y1, x2, y2 = boxes_xyxy[i]
            cls_id = classes[i]
            confidence = confidences[i]
            label = model.names[cls_id]
            obj_id = int(obj_id)

            # Cập nhật confidence history
            confidence_history[obj_id].append(confidence)
            
            # Chỉ xử lý nếu confidence đủ cao
            if confidence < MIN_CONFIDENCE:
                cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 0, 255), 1)
                cv2.putText(frame, f"{label} ID:{obj_id} [LOW CONF: {confidence:.2f}]", 
                           (int(x1), int(y1) - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
                continue

            # Lưu label của object
            object_labels[obj_id] = label
            
            # Tính tâm của object
            cx = (x1 + x2) / 2
            cy = (y1 + y2) / 2
            
            # Lưu trajectory
            object_trajectories[obj_id].append((cx, cy))
            
            # Kiểm tra action nếu đã có đủ trajectory
            if len(object_trajectories[obj_id]) >= TRAJECTORY_HISTORY // 2:
                action = detect_action(obj_id, object_trajectories[obj_id], ROI_BOX)
                
                if action:
                    # Kiểm tra cooldown để tránh duplicate
                    if current_time - last_action_time[obj_id] > action_cooldown:
                        # Tăng counter xác nhận
                        if obj_id not in pending_actions or pending_actions[obj_id].get('type') != action:
                            pending_actions[obj_id] = {
                                'type': action,
                                'label': label,
                                'confidence': confidence,
                                'start_time': current_time
                            }
                            action_confirm_counter[obj_id] = 1
                        else:
                            action_confirm_counter[obj_id] += 1
                        
                        # Xác nhận action nếu đủ số frame và confidence cao
                        avg_conf = get_avg_confidence(obj_id)
                        if action_confirm_counter[obj_id] >= ACTION_CONFIRM_FRAMES and avg_conf >= MIN_CONFIDENCE:
                            if action == 'VAO':
                                total_vao[label] += 1
                                log_msg = (f"[{time.strftime('%H:%M:%S')}] 🛒➕ {label} (ID:{obj_id}) "
                                          f"CHO VÀO GIỎ | Conf: {confidence:.3f} (Avg: {avg_conf:.3f}) | "
                                          f"Vào: {total_vao[label]} | Ra: {total_ra[label]} | "
                                          f"Trong giỏ: {total_vao[label] - total_ra[label]}")
                                print(log_msg)
                                log_records_vao.append(log_msg)
                                log_history.append(log_msg)
                                
                                # Cập nhật CSV
                                update_csv_quantities()
                            
                            elif action == 'RA':
                                total_ra[label] += 1
                                log_msg = (f"[{time.strftime('%H:%M:%S')}] 🛒➖ {label} (ID:{obj_id}) "
                                          f"LẤY RA KHỎI GIỎ | Conf: {confidence:.3f} (Avg: {avg_conf:.3f}) | "
                                          f"Vào: {total_vao[label]} | Ra: {total_ra[label]} | "
                                          f"Trong giỏ: {total_vao[label] - total_ra[label]}")
                                print(log_msg)
                                log_records_ra.append(log_msg)
                                log_history.append(log_msg)
                                
                                # Cập nhật CSV
                                update_csv_quantities()
                            
                            last_action_time[obj_id] = current_time
                            pending_actions.pop(obj_id, None)
                            action_confirm_counter[obj_id] = 0
                else:
                    # Reset counter nếu không phát hiện action
                    if obj_id in action_confirm_counter:
                        action_confirm_counter[obj_id] = max(0, action_confirm_counter[obj_id] - 1)
                        if action_confirm_counter[obj_id] == 0:
                            pending_actions.pop(obj_id, None)
            
            # Vẽ trajectory
            if len(object_trajectories[obj_id]) > 1:
                points = np.array(object_trajectories[obj_id], dtype=np.int32)
                for j in range(1, len(points)):
                    # Màu trajectory thay đổi theo action
                    if obj_id in pending_actions:
                        if pending_actions[obj_id]['type'] == 'VAO':
                            color = (0, 255, 0)  # Xanh lá cho VAO
                        else:
                            color = (0, 0, 255)  # Đỏ cho RA
                    else:
                        color = (255, 255, 0)  # Vàng cho neutral
                    
                    cv2.line(frame, tuple(points[j-1]), tuple(points[j]), color, 2)
            
            # Vẽ box với màu theo trạng thái
            roi_x1, roi_y1, roi_x2, roi_y2 = ROI_BOX
            in_roi = roi_x1 <= cx <= roi_x2 and roi_y1 <= cy <= roi_y2
            
            if obj_id in pending_actions:
                if pending_actions[obj_id]['type'] == 'VAO':
                    box_color = (0, 255, 0)
                    status = "ADDING"
                else:
                    box_color = (0, 0, 255)
                    status = "REMOVING"
                thickness = 3
            else:
                box_color = (255, 0, 0) if in_roi else (128, 128, 128)
                status = "IN ROI" if in_roi else "OUTSIDE"
                thickness = 2
            
            cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), box_color, thickness)
            
            # Hiển thị thông tin
            cv2.putText(frame, f"{label} ID:{obj_id} [{status}]", 
                       (int(x1), int(y1) - 25), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
            cv2.putText(frame, f"Conf: {confidence:.3f}", 
                       (int(x1), int(y1) - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.4, box_color, 1)

    # Cleanup old trajectories và pending actions
    for obj_id in list(object_trajectories.keys()):
        if obj_id not in detected_ids:
            if current_time - last_action_time.get(obj_id, 0) > 2.0:
                object_trajectories.pop(obj_id, None)
                confidence_history.pop(obj_id, None)
                pending_actions.pop(obj_id, None)
                action_confirm_counter.pop(obj_id, None)

    # Vẽ vùng giỏ hàng
    cv2.rectangle(frame, (ROI_BOX[0], ROI_BOX[1]), (ROI_BOX[2], ROI_BOX[3]), (0, 255, 0), 3)
    cv2.putText(frame, "SMART CART - ACTION DETECTION", (ROI_BOX[0] + 5, ROI_BOX[1] - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

    # Hiển thị thông tin giỏ hàng
    cv2.putText(frame, "San pham trong gio:", (start_x, start_y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
    
    y_offset = start_y + 25
    total_items = 0
    
    # Tính toán và hiển thị cho tất cả sản phẩm đã từng thấy
    all_labels = set(list(total_vao.keys()) + list(total_ra.keys()))
    for idx, label in enumerate(sorted(all_labels)):
        vao = total_vao[label]
        ra = total_ra[label]
        current_count = vao - ra
        total_items += max(0, current_count)  # Đảm bảo không âm
        
        # Màu sắc theo trạng thái
        if current_count > 0:
            text_color = (0, 255, 0)  # Xanh lá nếu có trong giỏ
        elif current_count < 0:
            text_color = (0, 0, 255)  # Đỏ nếu số âm (lỗi logic)
        else:
            text_color = (128, 128, 128)  # Xám nếu = 0
        
        cv2.putText(frame, f"{label}: {max(0, current_count)} (Vao: {vao}, Ra: {ra})", 
                   (start_x, y_offset + idx * 20),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.45, text_color, 1)

    # Hiển thị legend cho action detection
    legend_y = frame.shape[0] - 120
    cv2.putText(frame, "ACTION DETECTION:", (start_x, legend_y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    cv2.putText(frame, "- Green trajectory: ADDING", (start_x, legend_y + 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
    cv2.putText(frame, "- Red trajectory: REMOVING", (start_x, legend_y + 35),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
    cv2.putText(frame, "- Yellow trajectory: TRACKING", (start_x, legend_y + 50),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 0), 1)

    # Hiển thị thông tin CSV logging
    cv2.putText(frame, f"📊 CSV: {CSV_FILE}", 
                (start_x, legend_y + 70),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)

    # Hiển thị tổng số sản phẩm trong giỏ
    cv2.putText(frame, f"Tong san pham: {total_items}", (start_x, frame.shape[0] - 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)

    # Hiển thị frame
    cv2.imshow("Smart Cart - Action Detection", frame)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

# === Ghi log và thống kê cuối ===
end_time = time.time()
session_duration = end_time - start_time

print("\n=== THỐNG KÊ SMART CART - ACTION DETECTION ===")
all_labels = set(list(total_vao.keys()) + list(total_ra.keys()))
total_items = 0

for label in sorted(all_labels):
    vao = total_vao[label]
    ra = total_ra[label]
    current = vao - ra
    total_items += max(0, current)
    
    print(f"{label}:")
    print(f"  - Số lần cho vào: {vao}")
    print(f"  - Số lần lấy ra: {ra}")
    print(f"  - Hiện tại trong giỏ: {max(0, current)}")
    if current < 0:
        print(f"  ⚠️ CẢNH BÁO: Số lượng âm ({current}), có thể có lỗi tracking")
    print()

print(f"TỔNG SẢN PHẨM TRONG GIỎ: {total_items}")
print(f"⏱️ THỜI GIAN CHẠY: {session_duration:.1f} giây")

# Ghi log ra file text (giữ nguyên)
with open("cart_log_vao_actions.txt", "w", encoding="utf-8") as f_vao:
    f_vao.write("=== LOG ACTION CHO VÀO GIỎ ===\n")
    f_vao.write(f"Action Detection Settings: Movement Threshold={MIN_MOVEMENT_THRESHOLD}px, ")
    f_vao.write(f"Confirm Frames={ACTION_CONFIRM_FRAMES}\n\n")
    for record in log_records_vao:
        f_vao.write(record + "\n")

with open("cart_log_ra_actions.txt", "w", encoding="utf-8") as f_ra:
    f_ra.write("=== LOG ACTION LẤY RA KHỎI GIỎ ===\n")
    f_ra.write(f"Action Detection Settings: Movement Threshold={MIN_MOVEMENT_THRESHOLD}px, ")
    f_ra.write(f"Confirm Frames={ACTION_CONFIRM_FRAMES}\n\n")
    for record in log_records_ra:
        f_ra.write(record + "\n")

# Ghi thống kê cuối
with open("cart_statistics_actions.txt", "w", encoding="utf-8") as f_stats:
    f_stats.write("=== THỐNG KÊ SMART CART - ACTION DETECTION ===\n")
    f_stats.write(f"Session Duration: {session_duration:.1f} seconds\n")
    f_stats.write(f"Total Actions Logged: {len(log_records_vao) + len(log_records_ra)}\n\n")
    f_stats.write(f"Configuration:\n")
    f_stats.write(f"  - Min Confidence: {MIN_CONFIDENCE}\n")
    f_stats.write(f"  - High Confidence: {HIGH_CONFIDENCE}\n")
    f_stats.write(f"  - Movement Threshold: {MIN_MOVEMENT_THRESHOLD}px\n")
    f_stats.write(f"  - Action Confirm Frames: {ACTION_CONFIRM_FRAMES}\n")
    f_stats.write(f"  - Trajectory History: {TRAJECTORY_HISTORY} frames\n\n")
    
    total_items = 0
    for label in sorted(all_labels):
        vao = total_vao[label]
        ra = total_ra[label]
        current = vao - ra
        total_items += max(0, current)
        
        f_stats.write(f"{label}:\n")
        f_stats.write(f"  - Số lần cho vào (Vào): {vao}\n")
        f_stats.write(f"  - Số lần lấy ra (Ra): {ra}\n")
        f_stats.write(f"  - Hiện tại trong giỏ: {max(0, current)}\n")
        if current < 0:
            f_stats.write(f"  ⚠️ CẢNH BÁO: Số lượng âm ({current})\n")
        f_stats.write("\n")
    
    f_stats.write(f"TỔNG SẢN PHẨM TRONG GIỎ: {total_items}\n")

# === Cập nhật CSV cuối cùng ===
update_csv_quantities()

print(f"\n📁 Files created:")
print(f"   📊 CSV: {CSV_FILE}")
print(f"   📝 Text logs: cart_log_vao_actions.txt, cart_log_ra_actions.txt")
print(f"   📋 Statistics: cart_statistics_actions.txt")

cap.release()
cv2.destroyAllWindows()

print("\n=== CSV FILE SUMMARY ===")
try:
    with open(CSV_FILE, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        rows = list(reader)
        product_count = len(rows) - 1  # Trừ header
        print(f"📊 {CSV_FILE}: {product_count} products logged")
        
        # Hiển thị nội dung CSV
        print("\nCSV Contents:")
        print("Product | Quantity")
        print("-" * 20)
        for row in rows[1:]:  # Bỏ header
            if len(row) >= 2:
                print(f"{row[0]} | {row[1]}")
    
    print(f"\nCSV file can be opened in Excel or Google Sheets!")
    
except Exception as e:
    print(f"Error reading CSV file: {e}")
