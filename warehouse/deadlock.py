"""Deadlock handling on SHARED RESOURCES (packing stations, label printers,
dispatch bays) - tasks are the 'processes', resources are never workers/robots.

Resource vector order everywhere: [PackingStation, LabelPrinter, DispatchBay]
"""

RESOURCES = ["PackingStation", "LabelPrinter", "DispatchBay"]


def _le(a, b):
    return all(x <= y for x, y in zip(a, b))


def _add(a, b):
    return [x + y for x, y in zip(a, b)]


def _sub(a, b):
    return [x - y for x, y in zip(a, b)]


# ------------------------------------------------------------ Banker's Algorithm
def is_safe(available, maximum, allocation):
    """Safety algorithm. Returns (safe?, safe_sequence_as_indices)."""
    n = len(allocation)
    need = [_sub(maximum[i], allocation[i]) for i in range(n)]
    work, finish, seq = list(available), [False] * n, []
    progress = True
    while progress:
        progress = False
        for i in range(n):
            if not finish[i] and _le(need[i], work):
                work = _add(work, allocation[i])   # task finishes, releases all it holds
                finish[i] = True
                seq.append(i)
                progress = True
    return all(finish), seq


def request_resources(i, request, available, maximum, allocation):
    """Resource-request algorithm. Grants the request ONLY if the resulting
    state is safe. Returns (granted, reason, new_available, new_allocation, seq)."""
    need_i = _sub(maximum[i], allocation[i])
    if not _le(request, need_i):
        return False, "error: request exceeds declared maximum claim", available, allocation, []
    if not _le(request, available):
        return False, "must wait: resources not currently available", available, allocation, []
    new_avail = _sub(available, request)                      # pretend to allocate
    new_alloc = [row[:] for row in allocation]
    new_alloc[i] = _add(new_alloc[i], request)
    safe, seq = is_safe(new_avail, maximum, new_alloc)
    if safe:
        return True, "granted: state stays SAFE", new_avail, new_alloc, seq
    return False, "denied: would leave the system in an UNSAFE state", available, allocation, []


# ----------------------------------------------------------------- Detection
def detect_deadlock(available, allocation, request):
    """Deadlock-detection algorithm for multiple instances per resource type.
    Returns the list of deadlocked task indices (empty list = no deadlock)."""
    n = len(allocation)
    work = list(available)
    finish = [not any(allocation[i]) for i in range(n)]       # holds nothing => can't be deadlocked
    progress = True
    while progress:
        progress = False
        for i in range(n):
            if not finish[i] and _le(request[i], work):
                work = _add(work, allocation[i])
                finish[i] = True
                progress = True
    return [i for i in range(n) if not finish[i]]


def wait_for_cycle(allocation, request, available):
    """Wait-for graph: Ti -> Tj when Ti requests a resource type Tj holds and
    it is not available. Returns one cycle as a list of indices, or []."""
    n = len(allocation)
    edges = {i: set() for i in range(n)}
    for i in range(n):
        for r in range(len(RESOURCES)):
            if request[i][r] > available[r]:
                for j in range(n):
                    if j != i and allocation[j][r] > 0:
                        edges[i].add(j)

    def dfs(node, path, seen):
        if node in path:
            return path[path.index(node):] + [node]
        if node in seen:
            return []
        seen.add(node)
        for nxt in sorted(edges[node]):
            c = dfs(nxt, path + [node], seen)
            if c:
                return c
        return []

    seen = set()
    for s in range(n):
        c = dfs(s, [], seen)
        if c:
            return c
    return []


# ------------------------------------------------------------------ Recovery
def recover(names, priorities, available, allocation, request):
    """Process termination: repeatedly abort ONE victim (lowest priority = highest
    priority number; tie -> fewest resources held), release its resources and
    re-run detection until no deadlock remains. Returns (steps, victims)."""
    allocation = [row[:] for row in allocation]
    request = [row[:] for row in request]
    available = list(available)
    steps, victims = [], []
    while True:
        dead = detect_deadlock(available, allocation, request)
        if not dead:
            steps.append("no deadlock remains")
            return steps, victims
        steps.append("deadlocked: " + ", ".join(names[i] for i in dead))
        v = max(dead, key=lambda i: (priorities[i], -sum(allocation[i])))
        steps.append(f"abort victim {names[v]} (priority {priorities[v]}), "
                     f"releasing {dict(zip(RESOURCES, allocation[v]))}; task re-queued for restart")
        available = _add(available, allocation[v])
        allocation[v] = [0] * len(RESOURCES)
        request[v] = [0] * len(RESOURCES)
        victims.append(names[v])


# ---------------------------------------------------------------- Prevention
def ordered_request_ok(held, wanted):
    """Prevention by fixed request order (breaks circular wait): a task may only
    request a resource whose rank is HIGHER than every resource it already holds.
    `held` and `wanted` are resource names from RESOURCES (rank = list position)."""
    rank = {r: k for k, r in enumerate(RESOURCES)}
    return all(rank[wanted] > rank[h] for h in held)


# -------------------------------------------------- Four necessary conditions
def four_conditions(allocation, request, available):
    """Check the four Coffman conditions for the current state.
    mutual exclusion / no pre-emption are properties of the modelled resources
    (a printer or bay cannot be shared or taken away mid-use), so they are True by
    construction; hold-and-wait and circular wait are computed from the state."""
    hold_wait = any(any(allocation[i]) and any(request[i]) for i in range(len(allocation)))
    cycle = wait_for_cycle(allocation, request, available)
    return {"mutual_exclusion": True, "hold_and_wait": hold_wait,
            "no_preemption": True, "circular_wait": bool(cycle)}
