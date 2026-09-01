import os
import sys
import math
import json
import time
import random
import threading
import itertools
import functools

# =========================================================
# CONFIG
# =========================================================

NUM_CLASSES = 200
NUM_FUNCS_PER_CLASS = 20
NUM_GLOBAL_FUNCS = 2000

# =========================================================
# GLOBAL FUNCTIONS (mass generation)
# =========================================================

def _make_global_func(n):
    def func(x):
        total = 0
        for i in range(50):
            total += math.sin(i + x) * math.cos(i * x)
        return total + n
    func.__name__ = f"global_func_{n}"
    return func


GLOBAL_FUNCS = {}
for i in range(NUM_GLOBAL_FUNCS):
    f = _make_global_func(i)
    GLOBAL_FUNCS[f.__name__] = f
    globals()[f.__name__] = f

# =========================================================
# CLASSES (mass generation)
# =========================================================

class BaseWorker:
    def __init__(self, seed):
        self.seed = seed
        self.data = [random.random() for _ in range(100)]

    def compute(self):
        return sum(self.data) + self.seed


def _make_method(n):
    def method(self, x):
        result = 0
        for i in range(100):
            result += (i * x) % (n + 1)
        return result
    method.__name__ = f"method_{n}"
    return method


CLASSES = {}

for c in range(NUM_CLASSES):
    attrs = {}

    for m in range(NUM_FUNCS_PER_CLASS):
        method = _make_method(m)
        attrs[method.__name__] = method

    cls = type(f"Worker_{c}", (BaseWorker,), attrs)
    CLASSES[cls.__name__] = cls
    globals()[cls.__name__] = cls

# =========================================================
# THREAD WORKLOAD
# =========================================================

def worker_thread(idx):
    total = 0
    for i in range(500):
        fn = GLOBAL_FUNCS[f"global_func_{i % NUM_GLOBAL_FUNCS}"]
        total += fn(i)
    return total


def run_threads():
    threads = []
    results = []

    def target(i):
        results.append(worker_thread(i))

    for i in range(10):
        t = threading.Thread(target=target, args=(i,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    return sum(results)

# =========================================================
# MAIN EXECUTION
# =========================================================

def main():
    print("Starting stress test...")

    # Instantiate classes
    objs = [CLASSES[f"Worker_{i}"](i) for i in range(NUM_CLASSES)]

    total = 0

    # Run methods
    for obj in objs:
        for j in range(NUM_FUNCS_PER_CLASS):
            method = getattr(obj, f"method_{j}")
            total += method(j)

    # Run global funcs
    for i in range(1000):
        total += GLOBAL_FUNCS[f"global_func_{i % NUM_GLOBAL_FUNCS}"](i)

    # Run threads
    total += run_threads()

    # JSON + file ops
    data = {"result": total, "time": time.time()}
    path = os.path.join(os.getcwd(), "stress_output.json")

    with open(path, "w") as f:
        json.dump(data, f)

    print("Done.")
    print("Result:", total)


if __name__ == "__main__":
    main()
