# Lọc RSSI bằng trung bình trượt
class RSSIFilter:
    def __init__(self, window_size=5):
        self.window_size = window_size
        self.history = {}

    def update(self, beacon_id, rssi):
        if beacon_id not in self.history:
            self.history[beacon_id] = []
        self.history[beacon_id].append(rssi)
        if len(self.history[beacon_id]) > self.window_size:
            self.history[beacon_id].pop(0)
        return sum(self.history[beacon_id]) / len(self.history[beacon_id])
