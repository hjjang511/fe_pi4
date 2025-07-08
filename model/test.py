import joblib
import pandas as pd

model = joblib.load("model/ble_model.pkl")

test_inputs = [
    {"0-0": -54, "0-30": -52, "15-30": -48},
    {"0-0": -59, "0-30": -53, "15-30": -40},
    {"0-0": -70, "0-30": -67, "15-30": -35},
    {"0-0": -65, "0-30": -70, "15-30": -55},
]

for rssi in test_inputs:
    input_df = pd.DataFrame([rssi])
    output = model.predict(input_df)
    print(f"Input: {rssi} ? Predict: {output[0]}")
