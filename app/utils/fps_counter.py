import time

class FPSCounter:
    def __init__(self, avg_over=30):
        self._times   = []
        self._avg_over = avg_over

    def tick(self):
        self._times.append(time.time())
        if len(self._times) > self._avg_over:
            self._times.pop(0)

    @property
    def fps(self):
        if len(self._times) < 2:
            return 0.0
        elapsed = self._times[-1] - self._times[0]
        return round((len(self._times) - 1) / elapsed, 1) if elapsed > 0 else 0.0