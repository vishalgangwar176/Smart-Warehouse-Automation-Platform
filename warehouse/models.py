"""Task record shared by every scheduler (Review 1 style task record)."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Task:
    pid: str        # e.g. "T1"
    name: str       # warehouse activity
    category: str   # "urgent" | "normal" | "routine"  (used by Multilevel Queue)
    priority: int   # 1 = highest priority (ASSUMPTION - match your Review 1 scale)
    arrival: int    # arrival time (time units)
    burst: int      # CPU burst / processing time (time units)


# Demo dataset created for the live demo (NOT taken from Review 1 data).
SAMPLE_TASKS = [
    Task("T1", "Restock Cold Storage",    "routine", 4, 0, 8),
    Task("T2", "Pick Order #101",         "normal",  3, 1, 4),
    Task("T3", "Urgent Medical Dispatch", "urgent",  1, 2, 3),
    Task("T4", "Pack Order #102",         "normal",  2, 3, 5),
    Task("T5", "Inventory Audit",         "routine", 5, 4, 6),
    Task("T6", "Express Parcel",          "urgent",  1, 6, 2),
]

# Tiny sets whose answers can be worked out by hand on a whiteboard.
TINY_RR = [
    Task("A", "A", "normal", 1, 0, 5),
    Task("B", "B", "normal", 1, 1, 3),
    Task("C", "C", "normal", 1, 2, 1),
]
TINY_PRIO = [
    Task("A", "A", "normal", 2, 0, 3),
    Task("B", "B", "normal", 1, 1, 2),
]

# Starvation scenario: one routine task + a continuous stream of urgent tasks.
STARVATION = [Task("R1", "Inventory Audit", "routine", 5, 0, 4)] + [
    Task(f"U{i}", f"Urgent Parcel {i}", "urgent", 1, 1 + 2 * (i - 1), 2) for i in range(1, 9)
]
