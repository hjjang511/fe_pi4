# kalman.py
import numpy as np

class KalmanFilter2D:
    def __init__(self, process_variance=1e-4, measurement_variance=3.0):
        # Trạng thái: [x, y, vx, vy]
        self.x = np.zeros((4, 1))  # initial state [x, y, vx, vy]
        self.P = np.eye(4)         # initial uncertainty
        self.F = np.array([[1, 0, 1, 0],
                           [0, 1, 0, 1],
                           [0, 0, 1, 0],
                           [0, 0, 0, 1]])  # transition matrix
        self.H = np.array([[1, 0, 0, 0],
                           [0, 1, 0, 0]])  # observation matrix
        self.R = measurement_variance * np.eye(2)  # measurement noise
        self.Q = process_variance * np.eye(4)      # process noise

    def predict(self):
        self.x = self.F @ self.x
        self.P = self.F @ self.P @ self.F.T + self.Q

    def update(self, z):  # z: [x, y]
        z = np.reshape(z, (2, 1))
        y = z - self.H @ self.x
        S = self.H @ self.P @ self.H.T + self.R
        K = self.P @ self.H.T @ np.linalg.inv(S)

        self.x = self.x + K @ y
        self.P = (np.eye(4) - K @ self.H) @ self.P

    def get_position(self):
        return self.x[0, 0], self.x[1, 0]
    
    def set_position(self, position):  # [x, y]
        self.x = np.array([[position[0]], [position[1]], [0.0], [0.0]])
        self.P = np.eye(4)