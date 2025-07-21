import cv2
import numpy as np
import tensorflow as tf

# Load TFLite model and allocate tensors
interpreter = tf.lite.Interpreter(model_path="C:\\Users\\gvu03\\Desktop\\PyQtTestProject\\fe_pi4\\model\\my_model_saved_model\\my_model_float16.tflite")  # đổi thành đường dẫn file .tflite của bạn
interpreter.allocate_tensors()

# Get input and output tensors info
input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

# Class labels (đổi theo nhãn của bạn)
labels = {0: 'mirinda', 1: 'mleko', 2: 'number1', 3: 'obay', 4: 'steelseries'}

# Load input image
image = cv2.imread("test.jpg")  # thay bằng ảnh cần test
h, w = image.shape[:2]

# Preprocess: resize & normalize
input_shape = input_details[0]['shape']
resized = cv2.resize(image, (input_shape[2], input_shape[1]))
input_tensor = np.expand_dims(resized, axis=0).astype(np.uint8)

# Run inference
interpreter.set_tensor(input_details[0]['index'], input_tensor)
interpreter.invoke()
output_data = interpreter.get_tensor(output_details[0]['index'])

# Parse output (YOLOv8 format: (num_classes+4+1, num_boxes))
preds = np.squeeze(output_data)
num_boxes = preds.shape[1]

for i in range(num_boxes):
    # Extract values
    x, y, w_box, h_box = preds[0:4, i]
    conf = preds[4, i]
    class_probs = preds[5:, i]
    class_id = np.argmax(class_probs)
    score = class_probs[class_id] * conf

    if score > 0.4:
        # Convert to corner format
        x1 = int((x - w_box / 2) * w)
        y1 = int((y - h_box / 2) * h)
        x2 = int((x + w_box / 2) * w)
        y2 = int((y + h_box / 2) * h)

        label = labels.get(class_id, "Unknown")
        cv2.rectangle(image, (x1, y1), (x2, y2), (0,255,0), 2)
        cv2.putText(image, f"{label} {score:.2f}", (x1, y1 - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,0), 2)

# Show result
cv2.imshow("Detection", image)
cv2.waitKey(0)
cv2.destroyAllWindows()
