"""Concurrency layer: race condition + semaphore, bounded order buffer,
and a thread-state model for task sub-activities."""
import threading
import time
from enum import Enum


# ------------------------------------------- race condition vs. binary semaphore
def update_inventory(use_semaphore, workers=2, per_worker=50, start=1000):
    """`workers` threads each remove `per_worker` items one by one from a shared
    stock count. Expected final stock = start - workers*per_worker.

    The read-modify-write is the CRITICAL SECTION. The sleep(...) inside it
    forces a context switch so the lost-update race shows up every run."""
    state = {"stock": start}
    mutex = threading.Semaphore(1)            # binary semaphore

    def worker():
        for _ in range(per_worker):
            if use_semaphore:
                mutex.acquire()               # wait()  / P
            try:
                tmp = state["stock"]          # read
                time.sleep(0.0005)            # <- other thread can run here
                state["stock"] = tmp - 1      # write
            finally:
                if use_semaphore:
                    mutex.release()           # signal() / V

    threads = [threading.Thread(target=worker) for _ in range(workers)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return state["stock"], start - workers * per_worker


# ---------------------------------------------------- bounded order buffer
def bounded_buffer(orders, capacity=3, consumer_delay=0.02):
    """Producer = order intake, consumer = picking. Classic bounded buffer with
    counting semaphores `empty` (free slots) and `full` (filled slots) plus a
    mutex protecting the buffer itself."""
    buf, log, consumed = [], [], []
    empty = threading.Semaphore(capacity)
    full = threading.Semaphore(0)
    mutex = threading.Semaphore(1)
    stats = {"max": 0}
    log_lock = threading.Lock()

    def say(msg):
        with log_lock:
            log.append(msg)

    def producer():
        for o in orders:
            empty.acquire()                    # blocks if buffer is full
            mutex.acquire()
            buf.append(o)
            stats["max"] = max(stats["max"], len(buf))
            say(f"intake  PUT {o}   buffer={len(buf)}/{capacity}")
            mutex.release()
            full.release()

    def consumer():
        for _ in orders:
            full.acquire()                     # blocks if buffer is empty
            mutex.acquire()
            o = buf.pop(0)
            say(f"picking GOT {o}   buffer={len(buf)}/{capacity}")
            mutex.release()
            empty.release()
            consumed.append(o)
            time.sleep(consumer_delay)         # slow consumer => producer must wait

    p, c = threading.Thread(target=producer), threading.Thread(target=consumer)
    p.start(); c.start(); p.join(); c.join()
    return log, consumed, stats["max"]


# ------------------------------------------------ Readers-Writers (reader-preference)
def readers_writers(readers=4, writers=2, rounds=3):
    """Shared inventory record: many stock look-ups (readers) may overlap, but an
    update (writer) needs exclusive access. Classic first readers-writers
    solution: `mutex` protects read_count, `wrt` is held by the first reader in /
    last reader out, or by a writer."""
    mutex, wrt = threading.Semaphore(1), threading.Semaphore(1)
    state = {"read_count": 0, "active_r": 0, "active_w": 0, "max_r": 0, "violation": False}
    meta, log = threading.Lock(), []

    def note(msg):
        with meta:
            log.append(msg)

    def reader(i):
        for _ in range(rounds):
            mutex.acquire()
            state["read_count"] += 1
            if state["read_count"] == 1:
                wrt.acquire()                  # first reader locks writers out
            mutex.release()
            with meta:
                state["active_r"] += 1
                state["max_r"] = max(state["max_r"], state["active_r"])
                if state["active_w"]:
                    state["violation"] = True
            note(f"reader {i} reading")
            time.sleep(0.01)
            with meta:
                state["active_r"] -= 1
            mutex.acquire()
            state["read_count"] -= 1
            if state["read_count"] == 0:
                wrt.release()                  # last reader lets writers in
            mutex.release()

    def writer(i):
        for _ in range(rounds):
            wrt.acquire()
            with meta:
                state["active_w"] += 1
                if state["active_w"] > 1 or state["active_r"]:
                    state["violation"] = True
            note(f"WRITER {i} updating (exclusive)")
            time.sleep(0.01)
            with meta:
                state["active_w"] -= 1
            wrt.release()

    ts = [threading.Thread(target=reader, args=(i,)) for i in range(readers)]
    ts += [threading.Thread(target=writer, args=(i,)) for i in range(writers)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    return log, state["max_r"], state["violation"]


# ---------------------------------------------------------- thread-state model
class State(Enum):
    NEW = "NEW"
    READY = "READY"
    RUNNING = "RUNNING"
    WAITING = "WAITING"
    TERMINATED = "TERMINATED"


ALLOWED = {
    State.NEW: {State.READY},
    State.READY: {State.RUNNING},
    State.RUNNING: {State.WAITING, State.READY, State.TERMINATED},
    State.WAITING: {State.READY},
    State.TERMINATED: set(),
}


class SubActivity(threading.Thread):
    """One sub-activity (thread) of a warehouse task. All sub-activities of a
    task share `shared` (the task's data). States are a MODEL of thread states
    (NEW/READY/RUNNING/WAITING/TERMINATED); illegal transitions raise errors."""

    def __init__(self, name, shared, work, wait_for=None):
        super().__init__()
        self.label, self.shared, self.work, self.wait_for = name, shared, work, wait_for
        self.done = threading.Event()
        self.history = [State.NEW]

    def _go(self, s):
        if s not in ALLOWED[self.history[-1]]:
            raise RuntimeError(f"illegal transition {self.history[-1]} -> {s}")
        self.history.append(s)

    def run(self):
        self._go(State.READY)
        self._go(State.RUNNING)
        if self.wait_for is not None and not self.wait_for.is_set():
            self._go(State.WAITING)           # blocked on a dependency
            self.wait_for.wait()
            self._go(State.READY)
            self._go(State.RUNNING)
        self.work(self.shared)
        self._go(State.TERMINATED)
        self.done.set()


def run_task_threads():
    shared = {"task": "Pick Order #101", "log": []}

    def stock_check(d):
        time.sleep(0.2); d["log"].append("stock checked")

    def picking_list(d):
        d["log"].append("picking list built")

    def dispatch_doc(d):
        d["log"].append("dispatch document printed")

    t1 = SubActivity("stock check", shared, stock_check)
    t2 = SubActivity("picking list", shared, picking_list, wait_for=t1.done)
    t3 = SubActivity("dispatch document", shared, dispatch_doc, wait_for=t2.done)
    for t in (t3, t2, t1):                    # start the dependants first on purpose
        t.start()
    for t in (t1, t2, t3):
        t.join()
    return [t1, t2, t3], shared
