"""CPU-scheduling algorithms.

Every scheduler returns `ticks`: a list where ticks[t] is the pid running during
[t, t+1), or None if the CPU is idle. Metrics and Gantt charts are derived from
`ticks` in metrics.py, so all algorithms are measured in exactly the same way.
"""
from collections import deque


class _Arrivals:
    def __init__(self, tasks):
        self.pending = sorted(tasks, key=lambda t: (t.arrival, t.pid))
        self.i = 0

    def admit(self, upto):
        out = []
        while self.i < len(self.pending) and self.pending[self.i].arrival <= upto:
            out.append(self.pending[self.i])
            self.i += 1
        return out

    def more(self):
        return self.i < len(self.pending)


def _key(t):
    return (t.priority, t.arrival, t.pid)


# ------------------------------------------------------------------ Priority
def priority_non_preemptive(tasks):
    rem = {t.pid: t.burst for t in tasks}
    arr, ready, ticks, cur, t = _Arrivals(tasks), [], [], None, 0
    left = len(tasks)
    while left:
        ready += arr.admit(t)
        if cur is None and ready:
            cur = min(ready, key=_key)      # chosen once, then runs to completion
            ready.remove(cur)
        if cur is None:
            ticks.append(None)
        else:
            ticks.append(cur.pid)
            rem[cur.pid] -= 1
            if rem[cur.pid] == 0:
                cur = None
                left -= 1
        t += 1
    return ticks


def priority_preemptive(tasks):
    rem = {t.pid: t.burst for t in tasks}
    arr, ready, ticks, t = _Arrivals(tasks), [], [], 0
    left = len(tasks)
    while left:
        ready += arr.admit(t)
        if not ready:
            ticks.append(None)
        else:
            p = min(ready, key=_key)        # re-evaluated EVERY tick => pre-emption
            ticks.append(p.pid)
            rem[p.pid] -= 1
            if rem[p.pid] == 0:
                ready.remove(p)
                left -= 1
        t += 1
    return ticks


# --------------------------------------------------------------- Round Robin
def round_robin(tasks, quantum=2):
    rem = {t.pid: t.burst for t in tasks}
    arr, q, ticks, t = _Arrivals(tasks), deque(), [], 0
    while arr.more() or q:
        q.extend(x.pid for x in arr.admit(t))
        if not q:
            ticks.append(None)
            t += 1
            continue
        pid = q.popleft()
        run = min(quantum, rem[pid])
        ticks.extend([pid] * run)
        t += run
        rem[pid] -= run
        # tasks that arrived while pid ran join the queue BEFORE pid is re-queued
        q.extend(x.pid for x in arr.admit(t))
        if rem[pid] > 0:
            q.append(pid)
    return ticks


# ---------------------------------------------------------- Multilevel Queue
def multilevel_queue(tasks, quantum=2):
    """urgent -> pre-emptive priority, normal -> Round Robin, routine -> FCFS.

    A higher queue is always served first. A lower-queue task is pre-empted as
    soon as a higher-queue task is ready (a pre-empted Round Robin task goes to
    the FRONT of the normal queue and its quantum restarts)."""
    rem = {t.pid: t.burst for t in tasks}
    arr = _Arrivals(tasks)
    urgent, normal, routine = [], deque(), []
    cur, used, ticks, t, left = None, 0, [], 0, len(tasks)

    def admit(upto):
        for x in arr.admit(upto):
            {"urgent": urgent, "normal": normal, "routine": routine}[x.category].append(x)

    while left:
        admit(t)
        if urgent:
            if cur is not None:
                normal.appendleft(cur)
                cur, used = None, 0
            p = min(urgent, key=_key)
            ticks.append(p.pid)
            rem[p.pid] -= 1
            t += 1
            if rem[p.pid] == 0:
                urgent.remove(p)
                left -= 1
        elif normal or cur is not None:
            if cur is None:
                cur, used = normal.popleft(), 0
            ticks.append(cur.pid)
            rem[cur.pid] -= 1
            used += 1
            t += 1
            admit(t)
            if rem[cur.pid] == 0:
                left -= 1
                cur = None
            elif used == quantum:
                normal.append(cur)
                cur = None
        elif routine:
            p = min(routine, key=lambda x: (x.arrival, x.pid))      # FCFS
            ticks.append(p.pid)
            rem[p.pid] -= 1
            t += 1
            if rem[p.pid] == 0:
                routine.remove(p)
                left -= 1
        else:
            ticks.append(None)
            t += 1
    return ticks


# ------------------------------------------------- Multilevel Feedback Queue
def mlfq(tasks, quanta=(2, 4, 8), aging=10):
    """New tasks enter level 0. Using a full quantum demotes a task one level.
    A task that waits `aging` time units in a queue is promoted one level.
    Lower level number = higher priority; a ready higher level pre-empts."""
    rem = {t.pid: t.burst for t in tasks}
    arr = _Arrivals(tasks)
    levels = [deque() for _ in quanta]
    level, wait = {}, {}
    cur, used, ticks, t, left = None, 0, [], 0, len(tasks)
    last = len(quanta) - 1
    while left:
        for x in arr.admit(t):
            levels[0].append(x.pid)
            level[x.pid], wait[x.pid] = 0, 0
        top = next((l for l, d in enumerate(levels) if d), None)
        if cur is not None and top is not None and top < level[cur]:
            levels[level[cur]].appendleft(cur)      # pre-empted by a higher level
            wait[cur] = 0
            cur = None
        if cur is None:
            top = next((l for l, d in enumerate(levels) if d), None)
            if top is None:
                ticks.append(None)
                t += 1
                continue
            cur, used = levels[top].popleft(), 0
        ticks.append(cur)
        rem[cur] -= 1
        used += 1
        t += 1
        # aging: every task still waiting in a queue gets one unit older
        promote = []
        for l in range(1, len(levels)):
            for pid in levels[l]:
                wait[pid] += 1
                if wait[pid] >= aging:
                    promote.append((pid, l))
        for pid, l in promote:
            levels[l].remove(pid)
            level[pid] = l - 1
            levels[l - 1].append(pid)
            wait[pid] = 0
        if rem[cur] == 0:
            left -= 1
            cur = None
        elif used >= quanta[level[cur]]:
            level[cur] = min(level[cur] + 1, last)  # demotion after a full quantum
            levels[level[cur]].append(cur)
            wait[cur] = 0
            cur = None
    return ticks


ALGORITHMS = {
    "priority-np": ("Non-Pre-emptive Priority", priority_non_preemptive),
    "priority-p": ("Pre-emptive Priority", priority_preemptive),
    "rr": ("Round Robin", round_robin),
    "mlq": ("Multilevel Queue", multilevel_queue),
    "mlfq": ("Multilevel Feedback Queue", mlfq),
}
