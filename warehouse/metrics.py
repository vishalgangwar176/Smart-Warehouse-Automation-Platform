"""Waiting / turnaround / response time and an ASCII Gantt chart, from `ticks`."""


def compute_metrics(tasks, ticks):
    rows = []
    for t in tasks:
        idx = [i for i, p in enumerate(ticks) if p == t.pid]
        first, completion = idx[0], idx[-1] + 1
        tat = completion - t.arrival              # turnaround = completion - arrival
        rows.append({
            "pid": t.pid, "name": t.name, "arrival": t.arrival, "burst": t.burst,
            "completion": completion,
            "turnaround": tat,
            "waiting": tat - t.burst,             # waiting = turnaround - burst
            "response": first - t.arrival,        # response = first run - arrival
        })
    return rows


def context_switches(ticks):
    """Times the CPU moves directly from one task to a different task."""
    return sum(1 for a, b in zip(ticks, ticks[1:]) if a and b and a != b)


def segments(ticks):
    segs, start = [], 0
    for i in range(1, len(ticks) + 1):
        if i == len(ticks) or ticks[i] != ticks[start]:
            segs.append((start, i, ticks[start] or "idle"))
            start = i
    return segs


def gantt(ticks):
    cells = []
    for s, e, pid in segments(ticks):
        cells.append((s, e, pid, max((e - s) * 3, len(pid) + 2, len(str(e)) + 1)))
    bar = "|" + "|".join(pid.center(w) for _, _, pid, w in cells) + "|"
    axis = "".join(str(s).ljust(w + 1) for s, _, _, w in cells) + str(cells[-1][1])
    return bar + "\n" + axis


def report(title, tasks, ticks):
    rows = compute_metrics(tasks, ticks)
    out = [f"=== {title} ===", "Gantt chart:", gantt(ticks), "",
           f"{'Task':<5}{'Arr':>4}{'Burst':>6}{'Compl':>6}{'TAT':>5}{'WT':>5}{'RT':>5}"]
    for r in rows:
        out.append(f"{r['pid']:<5}{r['arrival']:>4}{r['burst']:>6}{r['completion']:>6}"
                   f"{r['turnaround']:>5}{r['waiting']:>5}{r['response']:>5}")
    n = len(rows)
    out.append(f"Average  WT={sum(r['waiting'] for r in rows)/n:.2f}  "
               f"TAT={sum(r['turnaround'] for r in rows)/n:.2f}  "
               f"RT={sum(r['response'] for r in rows)/n:.2f}  "
               f"Context switches={context_switches(ticks)}")
    return "\n".join(out)
