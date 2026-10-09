"""Live-demo runner.   python demo.py --help"""
import argparse

from warehouse.models import SAMPLE_TASKS, TINY_RR, TINY_PRIO, STARVATION
from warehouse.schedulers import ALGORITHMS, round_robin, mlfq
from warehouse.metrics import report, compute_metrics, context_switches
from warehouse import sync, deadlock as dl

# Silberschatz-style 5-task / 3-resource state (A=10, B=5, C=7 instances in total)
# mapped to [PackingStation, LabelPrinter, DispatchBay].
NAMES = ["T0", "T1", "T2", "T3", "T4"]
ALLOC = [[0, 1, 0], [2, 0, 0], [3, 0, 2], [2, 1, 1], [0, 0, 2]]
MAXIM = [[7, 5, 3], [3, 2, 2], [9, 0, 2], [2, 2, 2], [4, 3, 3]]
AVAIL = [3, 3, 2]


def show_tasks(tasks):
    print(f"{'Task':<5}{'Name':<26}{'Category':<9}{'Prio':>5}{'Arr':>5}{'Burst':>6}")
    for t in tasks:
        print(f"{t.pid:<5}{t.name:<26}{t.category:<9}{t.priority:>5}{t.arrival:>5}{t.burst:>6}")
    print()


def cmd_sched(a):
    tasks = {"sample": SAMPLE_TASKS, "tiny-rr": TINY_RR, "tiny-prio": TINY_PRIO}[a.dataset]
    show_tasks(tasks)
    title, fn = ALGORITHMS[a.algo]
    kw = {}
    if a.algo in ("rr", "mlq"):
        kw["quantum"] = a.quantum
        title += f" (quantum={a.quantum})"
    print(report(title, tasks, fn(tasks, **kw)))


def cmd_compare(a):
    tasks = STARVATION if a.scenario == "starvation" else SAMPLE_TASKS
    show_tasks(tasks)
    print(f"(Round Robin / MLQ quantum = {a.quantum}, MLFQ aging threshold = {a.aging})")
    print(f"{'Method':<30}{'avg WT':>8}{'avg TAT':>9}{'avg RT':>8}{'CtxSw':>7}{'max WT, routine':>17}")
    for key, (title, fn) in ALGORITHMS.items():
        kw = {"quantum": a.quantum} if key in ("rr", "mlq") else {"aging": a.aging} if key == "mlfq" else {}
        ticks = fn(tasks, **kw)
        rows = compute_metrics(tasks, ticks)
        n = len(rows)
        routine = [r["waiting"] for r, t in zip(rows, tasks) if t.category == "routine"]
        print(f"{title:<30}{sum(r['waiting'] for r in rows)/n:>8.2f}"
              f"{sum(r['turnaround'] for r in rows)/n:>9.2f}"
              f"{sum(r['response'] for r in rows)/n:>8.2f}"
              f"{context_switches(ticks):>7}{max(routine):>17}")


def cmd_quantum(a):
    show_tasks(SAMPLE_TASKS)
    print(f"{'quantum':<9}{'avg WT':>8}{'avg RT':>8}{'context switches':>18}")
    for q in (1, 2, 4, 8, 100):
        ticks = round_robin(SAMPLE_TASKS, q)
        rows = compute_metrics(SAMPLE_TASKS, ticks)
        n = len(rows)
        print(f"{q:<9}{sum(r['waiting'] for r in rows)/n:>8.2f}{sum(r['response'] for r in rows)/n:>8.2f}"
              f"{context_switches(ticks):>18}")
    print("\nSmall quantum -> many context switches; very large quantum -> behaves like FCFS.")


def cmd_race(a):
    for use_sem in (False, True):
        final, expected = sync.update_inventory(use_sem)
        label = "WITH binary semaphore   " if use_sem else "WITHOUT semaphore (race)"
        status = "CORRECT" if final == expected else f"WRONG (lost {final - expected} updates)"
        print(f"{label}: expected stock = {expected}, actual stock = {final}  -> {status}")


def cmd_buffer(a):
    orders = [f"ORD-{i}" for i in range(1, 9)]
    log, consumed, mx = sync.bounded_buffer(orders, capacity=a.capacity)
    print("\n".join(log))
    print(f"\nproduced in order : {orders}\nconsumed in order : {consumed}")
    print(f"max buffer occupancy = {mx} (capacity {a.capacity})  ->  "
          f"{'OK, never overflowed' if mx <= a.capacity else 'OVERFLOW'}")
    print(f"all orders delivered exactly once, in order: {consumed == orders}")


def cmd_rw(a):
    log, max_r, bad = sync.readers_writers()
    print("\n".join(log[:14]), "\n...")
    print(f"\nmax readers reading at the same time = {max_r}  (>1 proves readers overlap)")
    print(f"writer ever overlapped a reader/another writer: {bad}  ->  "
          f"{'MUTUAL EXCLUSION VIOLATED' if bad else 'OK, writers were always exclusive'}")


def cmd_threads(a):
    threads, shared = sync.run_task_threads()
    print(f"Task '{shared['task']}' - sub-activities run as threads sharing the task's data\n")
    for t in threads:
        print(f"{t.label:<18}: " + " -> ".join(s.value for s in t.history))
    print("\nshared task log:", shared["log"])


def cmd_banker(a):
    print("Resources:", dl.RESOURCES, " total = [10, 5, 7]")
    print("Available:", AVAIL)
    print(f"{'Task':<5}{'Allocation':<14}{'Max':<12}{'Need'}")
    for i, n in enumerate(NAMES):
        need = [m - x for m, x in zip(MAXIM[i], ALLOC[i])]
        print(f"{n:<5}{str(ALLOC[i]):<14}{str(MAXIM[i]):<12}{need}")
    safe, seq = dl.is_safe(AVAIL, MAXIM, ALLOC)
    print(f"\nSafety check: safe={safe}, safe sequence = <{', '.join(NAMES[i] for i in seq)}>")

    avail, alloc = AVAIL, ALLOC
    for who, req in ((1, [1, 0, 2]), (4, [3, 3, 0]), (0, [0, 2, 0])):
        ok, why, na, nb, s = dl.request_resources(who, req, avail, MAXIM, alloc)
        extra = f"  safe sequence <{', '.join(NAMES[i] for i in s)}>" if ok else ""
        print(f"\n{NAMES[who]} requests {req}: {why}{extra}")
        if ok:
            avail, alloc = na, nb
            print("   new Available:", avail)


def cmd_detect(a):
    names = ["T0", "T1", "T2"]
    alloc = [[0, 1, 0], [0, 0, 1], [1, 0, 0]]     # T0 holds printer, T1 holds bay, T2 holds station
    req = [[0, 0, 1], [0, 1, 0], [0, 0, 0]]       # T0 wants bay, T1 wants printer, T2 wants nothing
    avail, prio = [0, 0, 0], [2, 4, 3]
    print("Resources:", dl.RESOURCES)
    for n, x, r, p in zip(names, alloc, req, prio):
        print(f"{n} (priority {p}) holds {x}, requests {r}")
    dead = dl.detect_deadlock(avail, alloc, req)
    print("\nDetection ->", "DEADLOCK among " + ", ".join(names[i] for i in dead) if dead else "no deadlock")
    print("Four conditions:", dl.four_conditions(alloc, req, avail))
    cyc = dl.wait_for_cycle(alloc, req, avail)
    print("Circular wait reported:", " -> ".join(names[i] for i in cyc))
    print("\nRecovery (process termination):")
    steps, victims = dl.recover(names, prio, avail, alloc, req)
    for s in steps:
        print("  -", s)


def cmd_prevent(a):
    cases = [(["PackingStation"], "LabelPrinter"), (["DispatchBay"], "LabelPrinter"),
             ([], "DispatchBay")]
    print("Fixed request order:", " < ".join(dl.RESOURCES))
    for held, want in cases:
        ok = dl.ordered_request_ok(held, want)
        print(f"holds {held or 'nothing'} requests {want}: {'ALLOWED' if ok else 'REJECTED (would break the order -> no circular wait)'}")


def main():
    p = argparse.ArgumentParser(description="Smart Warehouse Automation Platform - demo runner")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("sched", help="run one scheduler and print Gantt chart + metrics")
    s.add_argument("algo", choices=list(ALGORITHMS))
    s.add_argument("--quantum", type=int, default=2)
    s.add_argument("--dataset", choices=["sample", "tiny-rr", "tiny-prio"], default="sample")
    s.set_defaults(fn=cmd_sched)

    s = sub.add_parser("compare", help="all five methods on the same task set")
    s.add_argument("--quantum", type=int, default=2)
    s.add_argument("--aging", type=int, default=10)
    s.add_argument("--scenario", choices=["sample", "starvation"], default="sample")
    s.set_defaults(fn=cmd_compare)

    sub.add_parser("quantum", help="Round Robin: effect of the time quantum").set_defaults(fn=cmd_quantum)
    sub.add_parser("race", help="race condition vs binary semaphore").set_defaults(fn=cmd_race)
    s = sub.add_parser("buffer", help="bounded order buffer (counting semaphores)")
    s.add_argument("--capacity", type=int, default=3)
    s.set_defaults(fn=cmd_buffer)
    sub.add_parser("rw", help="Readers-Writers on the shared inventory record").set_defaults(fn=cmd_rw)
    sub.add_parser("threads", help="task sub-activities as threads + thread states").set_defaults(fn=cmd_threads)
    sub.add_parser("banker", help="Banker's Algorithm: safety check + resource requests").set_defaults(fn=cmd_banker)
    sub.add_parser("detect", help="deadlock detection, circular wait, recovery").set_defaults(fn=cmd_detect)
    sub.add_parser("prevent", help="deadlock prevention by fixed request order").set_defaults(fn=cmd_prevent)

    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
