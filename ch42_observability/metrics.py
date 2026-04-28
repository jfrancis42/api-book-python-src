import threading
from collections import defaultdict


class Metrics:
    def __init__(self):
        self._lock = threading.Lock()
        self._request_counts: dict[tuple, int] = defaultdict(int)
        self._latency_sum: dict[tuple, float] = defaultdict(float)
        self._latency_count: dict[tuple, int] = defaultdict(int)

    def record(self, method: str, path: str, status: int, duration_ms: float) -> None:
        with self._lock:
            self._request_counts[(method, path, status)] += 1
            self._latency_sum[(method, path)] += duration_ms
            self._latency_count[(method, path)] += 1

    def summary(self) -> dict:
        with self._lock:
            result: dict = {"requests": {}, "latency_avg_ms": {}}
            for (method, path, status), count in self._request_counts.items():
                result["requests"][f"{method} {path} {status}"] = count
            for (method, path), total in self._latency_sum.items():
                n = self._latency_count[(method, path)]
                result["latency_avg_ms"][f"{method} {path}"] = round(total / n, 1)
            return result

    def reset(self) -> None:
        with self._lock:
            self._request_counts.clear()
            self._latency_sum.clear()
            self._latency_count.clear()


metrics = Metrics()
