from ultralytics import YOLO

model = YOLO('my_model.pt')
print(model.names)           # In ra danh sách class
print(len(model.names))      # Số lượng class
