# Smart Warehouse Automation Platform (OS PBL)

An **Operating Systems simulation** that models warehouse operations as OS processes. Built incrementally across PBL reviews for the Operating Systems course at NIET.

| | |
|---|---|
| **Course** | Operating Systems (CCSE0303A) |
| **Program** | B.Tech CSE |
| **Faculty** | Dr. Neeti Taneja |
| **Team / Group No.** | 103 |
| **SDG** | SDG 9 – Industry, Innovation and Infrastructure |
| **Current Milestone** | Review 2 – Development & Application (Month 2) |
| **Overall Progress** | 60% |

---

## 1. Overview

```
Warehouse Task = Simulated OS Process
```

Each warehouse task (picking, packing, urgent orders, etc.) is treated as a process with arrival time, burst time and priority. The platform schedules these tasks on a simulated CPU, protects shared data with synchronization primitives, and handles deadlocks over shared warehouse resources.

**What this project is not:** it does **not** control physical robots, workers, IoT hardware or real warehouse machinery. Only *shared resources* (packing stations, label printers, dispatch bays) are modelled for deadlock handling — robots and workers are never treated as processes.

The project is extended review by review, and **earlier modules are kept unchanged**; new concepts are added as extensions.

---

## 2. Roadmap

| Review | Scope | Status |
|---|---|---|
| **Review 1** | Unit 1 & Unit 2 up to Priority Scheduling: PCB, ready queue, CPU simulation, Non-Pre-emptive and Pre-emptive Priority Scheduling, metrics, Gantt charts | Done |
| **Review 2** | Remaining Unit 2 (Round Robin, Multilevel Queue, Multilevel Feedback Queue, threads) and Unit 3 (synchronization, deadlocks) | Done (60%) |
| **Final Review** | Unit 4 (Memory Management), final integration, validation with more test cases, final report | Planned |

---

## 3. Features

### Review 1: Priority scheduling baseline
- Warehouse tasks as processes with a simplified **Process Control Block (PCB)** and states `NEW → READY → RUNNING → TERMINATED`
- Priority-ordered **ready queue** with FCFS tie-breaking
- Single-core **simulated CPU** and short-term scheduler
- **Non-Pre-emptive** and **Pre-emptive** Priority Scheduling
- Metrics: Completion Time, Turnaround Time, Waiting Time, Response Time, and their averages
- Event logs and terminal-rendered **ASCII Gantt charts**

### Review 2: Scheduling extensions
| Scheduler | How it works in the warehouse |
|---|---|
| **Round Robin** | Fixed, **configurable time quantum**; an unfinished task returns to the back of the queue |
| **Multilevel Queue (MLQ)** | Urgent queue → Pre-emptive Priority; Normal queue → Round Robin; Routine queue → FCFS. Higher queues are served first |
| **Multilevel Feedback Queue (MLFQ)** | Tasks start at the top level, drop a level after using a full quantum, and are promoted by **aging** if they wait too long |

The quantum is configurable on purpose: a very small value causes many context switches, and a very large one behaves like FCFS. All new schedulers use the same task record as Review 1.

### Review 2: Threads
- Sub-activities of a task (stock check, picking list, dispatch document) are modelled as **threads** that share the task's data, mapped to thread states
- Studied: process vs thread, benefits, thread types, multithreading models (hyper-threading studied as a concept only)

### Review 2: Process synchronization
- **Race condition demonstration:** two tasks updating one inventory count can lose an update
- **Critical section** guarded by a **binary semaphore** (mutual exclusion) for the shared inventory update
- **Bounded Buffer (producer–consumer):** an order buffer between intake and picking, using counting semaphores for empty and full slots
- Lock variables and strict alternation were rejected: a lock variable does not guarantee mutual exclusion, and strict alternation can block a task
- Studied as models: Dining Philosophers, Sleeping Barber; Readers-Writers applied

### Review 2: Deadlock handling
- Checks the four conditions: mutual exclusion, hold and wait, no pre-emption, circular wait
- **Prevention:** fixed resource request order
- **Avoidance:** **Banker's Algorithm** safety check; a request is granted only in a safe state
- **Detection and recovery:** circular waits are reported; recovery ends or restarts a task to release its resources

---

## 4. Priority Mapping & Task Types

Priority scale: **1 = Urgent (highest), 2 = Normal, 3 = Routine (lower)**.

| Warehouse Task | Priority | Description |
|---|---|---|
| Urgent Order Processing | 1 | Express shipments needing immediate fulfilment |
| Normal Order Processing | 2 | Standard customer orders |
| Picking | 2 | Item retrieval from storage bins |
| Packing | 2 | Boxing and sealing picked goods |
| Dispatch Preparation | 2 | Manifesting and staging goods at loading docks |
| Inventory Update | 3 | Periodic stock reconciliation |
| Restocking | 3 | Replenishing shelves from bulk receiving |

---

## 5. Project Structure

```
smart-warehouse-automation-platform/
├── src/
│   ├── pcb.py             # Process Control Block & ProcessState enum
│   ├── task_types.py      # Warehouse task types and priority mapping
│   ├── ready_queue.py     # Priority queue with FCFS tie-breaking
│   ├── cpu.py             # Simulated CPU
│   ├── scheduler.py       # Non-Pre-emptive & Pre-emptive Priority schedulers
│   ├── metrics.py         # CT, TAT, WT, RT and averages
│   ├── gantt.py           # ASCII Gantt chart & table renderers
│   └── ...                # Review 2 modules: Round Robin, MLQ, MLFQ,
│                          # threads, semaphores, Banker's Algorithm
├── tests/                 # Automated unit tests
├── index.html             # Web front end
├── app.js
├── style.css
├── main.py                # CLI demo and comparative benchmark runner
├── run_simulation.bat     # Windows launcher
├── .gitignore
└── README.md
```

> Update the `...` line with your actual Review 2 file names once they are final.

---

## 6. How to Run

**Prerequisites:** Python 3.8+ (standard library only, no external packages).

```bash
# Run automated tests
python -m unittest discover -s tests -p "test_*.py" -v

# Run all demonstrations
python main.py --demo

# Run individual test cases
python main.py --case1   # Urgent order pre-emption
python main.py --case2   # 4-process comparative benchmark
python main.py --case3   # Full 7-task warehouse workload
```

On Windows you can also double-click `run_simulation.bat` or run `.\run_simulation.bat` in PowerShell.

For the web front end, open `index.html` in a browser.

---

## 7. Sample Results (Review 1 baseline)

These come from the Priority Scheduling baseline, which Review 2 keeps unchanged.

### Test Case 1: Urgent order pre-empts routine restocking

| PID | Task | Priority | AT | BT |
|---|---|---|---|---|
| P1 | Restocking | 3 | 0 | 8 |
| P2 | Urgent Order Processing | 1 | 2 | 3 |

```
Pre-emptive Gantt:
+--------+---------+------------------+
|   P1   |    P2   |        P1        |
+--------+---------+------------------+
0        2         5                 11
```

| Metric | Non-Pre-emptive | Pre-emptive |
|---|---|---|
| Avg Turnaround Time | 8.50 | **7.00** |
| Avg Waiting Time | 3.00 | **1.50** |
| Avg Response Time | 3.00 | **0.00** |

### Test Case 2: Staggered 4-process benchmark

| Metric | Non-Pre-emptive | Pre-emptive |
|---|---|---|
| Avg Turnaround Time | 8.50 | **8.00** |
| Avg Waiting Time | 4.75 | **4.25** |
| Avg Response Time | 4.75 | **3.75** |

### Test Case 3: Full 7-task workload

| Metric | Non-Pre-emptive | Pre-emptive |
|---|---|---|
| Avg Turnaround Time | 10.71 | **10.00** |
| Avg Waiting Time | 7.43 | **6.71** |
| Avg Response Time | 7.43 | **4.29** |

### Review 2 outcomes

The same task set can now be scheduled with **five methods**: Non-Pre-emptive Priority, Pre-emptive Priority, Round Robin, Multilevel Queue and Multilevel Feedback Queue.

- Round Robin and MLFQ bound the waiting time of routine tasks, reducing **starvation**, at the cost of more context switches.
- The semaphore keeps the shared inventory count consistent.
- Unsafe resource requests are held back by Banker's Algorithm, and circular waits are reported.

Full numerical comparisons across all five schedulers will be consolidated in the final report.

---

## 8. Case Studies

- **RTOS scheduling:** priority-driven pre-emptive scheduling (Liu & Layland)
- **Database deadlock avoidance:** applied to shared-resource deadlock handling

---

## 9. Challenges & Solutions

| Challenge | Solution |
|---|---|
| Choosing a time quantum | Made it configurable and tested more than one value |
| Keeping Review 1 modules working | Added new schedulers separately and re-ran Review 1 tests |
| Modelling deadlock without treating robots or workers as processes | Modelled only shared resources (packing stations, label printers, dispatch bays) |

---

## 10. Team

| Member | Contribution |
|---|---|
| **Vinayak Dev Tiwari** | OS concept analysis (Unit 2 remaining, Unit 3); synchronization (semaphore, bounded buffer) and deadlock modules (Banker's Algorithm, detection, recovery); integration of all modules; repository management |
| **Tanay Dubey** | RTOS and database deadlock-avoidance case studies; mapping threads, resources and task types to the warehouse; project plan for the next review |
| **Vishal Gangwar** | Round Robin (configurable quantum) and Multilevel Queue; test scenarios and expected outputs; race-condition demonstration |
| **Vikas Pal** | Multilevel Feedback Queue (demotion and aging); metric analysis against Priority Scheduling; GitHub updates |
| **Urvashi Anand** | Documentation, evidence collection (outputs, Gantt charts, notes) and report preparation |

---

## 11. Next Steps

- Validate all five scheduling methods plus the synchronization and deadlock modules with more test cases
- Add Memory Management (Unit 4) without changing working code
- Prepare the final report and update the repository and evidence

---

## 12. References

1. A. Silberschatz, P. B. Galvin and G. Gagne, *Operating System Concepts*, 10th ed., Wiley, 2018.
2. C. L. Liu and J. W. Layland, "Scheduling Algorithms for Multiprogramming in a Hard-Real-Time Environment," *Journal of the ACM*, vol. 20, no. 1, pp. 46–61, 1973.

No external dataset was used; the warehouse task categories and priority scale are the same as in Review 1.
