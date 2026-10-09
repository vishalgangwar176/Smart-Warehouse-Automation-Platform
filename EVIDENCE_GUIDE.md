# Smart Warehouse Automation Platform — Live Demo & Evidence Guide

**Report audited:** `NIET_OS_PBL_REPORT_2.docx` (PBL Progress Report II, Group 103)
**Repo audited:** https://github.com/vishalgangwar176/Smart-Warehouse-Automation-Platform
**Audit date:** 9 Oct 2026

---

## 0. Read this first — what was and was not found

| Check | Result |
|---|---|
| Report text read | Yes, in full (13-row review table, 2 cited sources) |
| GitHub repo contents | **The public repo page says "This repository is empty."** No commits/files were visible. Only the repo *description* exists (it lists the same features the report claims). |
| Review 1 code / data | Not available (neither in the report nor the repo) |

**Consequence:** For *your team's own code*, every feature is **Evidence not found** (in the public repo).

To avoid leaving you with nothing, a **reference implementation** of every claimed feature was written for this guide (all under this folder, Python standard library only, 19 automated tests passing). Everything in sections 2–4 refers to **that** code. Labels used below:

* **Verified in code / Runnable demo available** = exists in this reference implementation and was executed; outputs shown are real outputs from a run.
* **Report claim only** = the report says it, but no code exists or can exist (theory/case-study/documentation).
* **Evidence not found** = the claim cannot be checked against *your team's* repo.

> ⚠️ **Academic-integrity note.** Your report declares that AI-generated content may be penalised. This code was written for you here, it is **not** the code your team committed. Do not present it as already being in the team's GitHub history. Either (a) if teammates have the real code locally (the report says Vinayak manages the repo), push *that* and map this guide onto it, or (b) if you use this code, disclose AI assistance as your course policy requires, and make sure you can explain every function below.
>
> Also: the **task data** (`SAMPLE_TASKS`) is invented for the demo, and `priority 1 = highest` is an **assumption** — your Review 1 scale/data were not visible. Change `warehouse/models.py` to match.

---

## 1. One-time setup (VS Code terminal)

```bash
# Requires Python 3.8+ ; no pip installs needed
python --version            # on Windows, if this fails use:  py --version
cd Smart-Warehouse-Automation-Platform
python -m unittest -v       # runs all 19 tests -> expect "Ran 19 tests ... OK"
python demo.py --help
```

Publish to your repo (so the GitHub link in the report is no longer empty):

```bash
git clone https://github.com/vishalgangwar176/Smart-Warehouse-Automation-Platform
# copy the project files into that folder, then:
git add . && git commit -m "Add scheduling, synchronization and deadlock modules with tests" && git push
```

File map (line numbers are from this reference implementation):

| File | Contents |
|---|---|
| `warehouse/models.py` | `Task` record (l.6), `SAMPLE_TASKS` (l.16), `TINY_RR` (l.26), `TINY_PRIO` (l.31), `STARVATION` (l.37) |
| `warehouse/schedulers.py` | 5 schedulers |
| `warehouse/metrics.py` | WT / TAT / RT, context switches, Gantt |
| `warehouse/sync.py` | race + semaphore, bounded buffer, readers-writers, thread states |
| `warehouse/deadlock.py` | Banker's, detection, wait-for cycle, recovery, prevention, four conditions |
| `demo.py` | CLI used for the live demo |
| `tests/test_all.py` | 19 tests (some with hand-calculated expected values) |

---

## 2. Feature-by-feature evidence

Report claim → where the report says it → status → code → run → expected output → what to say.

### F1. Non-Pre-emptive Priority  (report rows 6, 8; Review 1 baseline)
* **Status:** Verified in code · Runnable demo available (your *actual* Review 1 code: Evidence not found)
* **Code:** `warehouse/schedulers.py` → `priority_non_preemptive()` l.31–49
* **Run:**
  ```bash
  python demo.py sched priority-np
  ```
* **Input:** the 6 tasks printed at the top (T1 arrives at 0, burst 8, priority 4 …).
* **Expected output (real):**
  ```
  |           T1           |    T3   |  T6  |       T4      |     T2     |        T5        |
  0                        8         11     13              18           22                 28
  Average  WT=9.33  TAT=14.00  RT=9.33  Context switches=5
  ```
* **Say:** "T1 arrived first and started at 0. Even though urgent T3 arrives at time 2, non-pre-emptive priority cannot interrupt it, so T3 waits until 8. After each finish the scheduler picks the best priority number among arrived tasks."

### F2. Pre-emptive Priority  (rows 3, 6, 8)
* **Status:** Verified in code · Runnable demo
* **Code:** `priority_preemptive()` l.52–68
* **Run (hand-checkable 2-task case):**
  ```bash
  python demo.py sched priority-p --dataset tiny-prio
  ```
* **Expected (real):** `| A |  B   |  A   |` / `0 1 3 5`, B: WT 0, A: WT 2.
* **Say:** "A (priority 2) starts at 0. B (priority 1, more urgent) arrives at 1 and takes the CPU immediately; A resumes at 3 and finishes at 5. The test `test_preemptive_priority_hand` asserts exactly this."
* Full set: `python demo.py sched priority-p`

### F3. Round Robin, configurable quantum  (rows 4, 6, 7)
* **Status:** Verified in code · Runnable demo
* **Code:** `round_robin(tasks, quantum=2)` l.72–90
* **Run (whiteboard case):**
  ```bash
  python demo.py sched rr --dataset tiny-rr --quantum 2
  ```
* **Input:** A(arr 0, burst 5), B(1, 3), C(2, 1).
* **Expected (real):**
  ```
  |  A   |  B   | C |  A   | B | A |
  0      2      4   5      7   8   9
  Task  Arr Burst Compl  TAT   WT   RT
  A       0     5     9    9    4    0
  B       1     3     8    7    4    1
  C       2     1     5    3    2    2
  ```
* **Say:** "Each task gets at most 2 units, then goes to the back of the queue. Tasks that arrive while another is running join the queue *before* the pre-empted task. TAT = completion − arrival, WT = TAT − burst, RT = first run − arrival. I worked this out by hand first; the unit test checks the same numbers."
* **Quantum trade-off (report row 7):**
  ```bash
  python demo.py quantum
  ```
  Real output: quantum 1 → 27 context switches; 2 → 14; 4 → 8; 8 and 100 → 5 (identical = behaves like FCFS).

### F4. Multilevel Queue (urgent = pre-emptive priority, normal = RR, routine = FCFS)  (rows 4, 6, 7)
* **Status:** Verified in code · Runnable demo
* **Code:** `multilevel_queue()` l.94–147
* **Run:** `python demo.py sched mlq --quantum 2`
* **Expected (real):**
  ```
  | T1 | T2 |    T3   | T2 |  T6  |  T2  |       T4      |          T1         |        T5        |
  0    1    2         5    6      8      10              15                    22                 28
  Average  WT=7.33  TAT=12.00  RT=4.17  Context switches=8
  ```
* **Say:** "T1 is routine so it only runs while nothing higher is ready — at time 1 normal task T2 pre-empts it, at time 2 urgent T3 pre-empts T2, and at 6 urgent T6 interrupts T2 again. The routine tasks T1/T5 run last, in arrival order (FCFS)."
* **Design choices to state honestly:** a pre-empted RR task goes to the *front* of the normal queue with its quantum restarted. The report doesn't specify this; it's a choice.

### F5. Multilevel Feedback Queue (demotion + aging)  (rows 4, 6, 7)
* **Status:** Verified in code · Runnable demo
* **Code:** `mlfq(tasks, quanta=(2,4,8), aging=10)` l.151–201 (aging l.181–192, demotion l.197)
* **Run:** `python demo.py sched mlfq`
* **Expected (real):** `Average WT=12.50 TAT=17.17 RT=2.33 Context switches=12`
* **Say:** "Every task starts at level 0 with quantum 2. If it uses the whole quantum it drops a level (quantum 4, then 8). If it waits ≥ 10 units in a lower queue it is promoted — that's aging. Lowest response time of all five methods (2.33) because every new task gets the CPU quickly."
* Assumptions: 3 levels, quanta 2/4/8, aging 10 — report gives no numbers.

### F6. Waiting / turnaround / response time + Gantt charts  (rows 6, 8, 9)
* **Status:** Verified in code · Runnable (text Gantt in terminal; the report's image Gantt charts: Evidence not found)
* **Code:** `warehouse/metrics.py` → `compute_metrics()` l.4, `context_switches()` l.20, `gantt()` l.34–40
* **Run:** any `sched` command above.

### F7. Five methods compared on one task set; "RR and MLFQ bound routine-task waiting, reducing starvation, at the cost of more context switches"  (row 8)
* **Status:** Runnable demo. Claim is **partly supported — be careful**.
* **Code:** `demo.py` → `cmd_compare()` l.35–49
* **Run:**
  ```bash
  python demo.py compare
  python demo.py compare --scenario starvation --aging 4
  ```
* **What the data shows (real):**
  * On the normal 6-task set (`compare`), the worst routine-task wait is **18 for every method** → this set does **not** demonstrate the starvation claim. Don't use it for that.
  * On the starvation set (1 routine task + a continuous stream of 8 urgent tasks):

    | Method | Routine task R1 waiting |
    |---|---|
    | Pre-emptive Priority | 16 |
    | Multilevel Queue | 16 (no feedback → no help) |
    | Round Robin (q=2) | **2** |
    | MLFQ aging 10 | 12 |
    | MLFQ aging 4 | **6** |
  * Context switches: RR 14 vs Non-pre-emptive 5 on the main set → the "more context switches" part holds.
* **Say:** "Priority-based methods starve the routine task as long as urgent work keeps arriving. Round Robin and MLFQ-with-aging guarantee it eventually runs. Note MLQ alone doesn't help — that's exactly why feedback and aging exist." (Test: `test_starvation_claim`.)
* Whether this matches your **Review 1 priority module** or its metrics: Evidence not found.

### F8. Threads: process vs thread, thread states, sub-activities sharing task data  (rows 4, 6)
* **Status:** Verified in code (as a *model*) · Runnable demo. "Types, benefits, multithreading models" and **hyper-threading** = **Report claim only** (theory; the report itself says hyper-threading is a concept only).
* **Code:** `warehouse/sync.py` → `State` l.139, `SubActivity` l.156, `run_task_threads()` l.185
* **Run:** `python demo.py threads`
* **Expected (real):**
  ```
  stock check       : NEW -> READY -> RUNNING -> TERMINATED
  picking list      : NEW -> READY -> RUNNING -> WAITING -> READY -> RUNNING -> TERMINATED
  dispatch document : NEW -> READY -> RUNNING -> WAITING -> READY -> RUNNING -> TERMINATED
  shared task log: ['stock checked', 'picking list built', 'dispatch document printed']
  ```
* **Say:** "Three real Python threads are the sub-activities of one task; they share the task's data dictionary. The picking list can't start until stock check is done, and dispatch can't start until the list is built — so they pass through WAITING. Illegal state changes raise an error. These states model the textbook thread life-cycle; they are not OS-kernel states."

### F9. Race condition + binary semaphore on the shared inventory update  (rows 4, 6, 7, 8)
* **Status:** Verified in code · Runnable demo
* **Code:** `update_inventory(use_semaphore, …)` `warehouse/sync.py` l.9–35 (critical section l.23–25: read, sleep, write)
* **Run:** `python demo.py race`
* **Input:** stock 1000; 2 threads each remove 50 items one at a time → correct = 900.
* **Expected (real):**
  ```
  WITHOUT semaphore (race): expected stock = 900, actual stock = 950  -> WRONG (lost 50 updates)
  WITH binary semaphore   : expected stock = 900, actual stock = 900  -> CORRECT
  ```
  (Unsafe value can vary run to run but is always **> 900**; the test asserts that.)
* **Say:** "Both threads read the same stock value, then both write value−1, so one decrement vanishes — a lost update. A deliberate 0.5 ms sleep inside the critical section makes it happen every time instead of rarely. With `Semaphore(1)` only one thread is in the read-modify-write at a time."

### F10. Bounded order buffer with counting semaphores  (rows 4, 6, 7)
* **Status:** Verified in code · Runnable demo
* **Code:** `bounded_buffer()` l.39–77 (`empty`, `full`, `mutex`)
* **Run:** `python demo.py buffer` (try `--capacity 1`)
* **Expected (real, last lines):**
  ```
  produced in order : ['ORD-1', ... 'ORD-8']
  consumed in order : ['ORD-1', ... 'ORD-8']
  max buffer occupancy = 3 (capacity 3)  ->  OK, never overflowed
  all orders delivered exactly once, in order: True
  ```
  The log shows intake stalling at `buffer=3/3` until picking removes an order.
* **Say:** "`empty` counts free slots, `full` counts filled slots. Intake blocks when full, picking blocks when empty, and a mutex protects the list itself — producer-consumer."

### F11. Readers-Writers  (row 4 says "applied")
* **Status:** Verified in code · Runnable demo (*added because the report claims it; not in the report's "work completed" list*)
* **Code:** `readers_writers()` l.81–135
* **Run:** `python demo.py rw`
* **Expected (real):** `max readers reading at the same time = 4` and `writer ever overlapped a reader/another writer: False -> OK`.
* **Say:** "Many stock look-ups may overlap; an update gets exclusive access. First reader in locks writers out, last reader out lets them in. This is the reader-preference version, so writers can wait a long time — a known trade-off."

### F12. Banker's Algorithm (safety check + resource-request)  (rows 2, 4, 6, 7, 8)
* **Status:** Verified in code · Runnable demo. **This is the real Banker's Algorithm, not a bank-account feature.** (There is no bank-account feature anywhere in the report or reference code.)
* **Code:** `warehouse/deadlock.py` → `is_safe()` l.23, `request_resources()` l.40
* **Run:** `python demo.py banker`
* **Input:** 5 tasks T0–T4, resources [PackingStation, LabelPrinter, DispatchBay] with totals [10,5,7], Available [3,3,2], Allocation/Max tables printed on screen. (This is the standard 5-process/3-resource textbook example, relabelled to warehouse resources.)
* **Expected (real):**
  ```
  Safety check: safe=True, safe sequence = <T1, T3, T4, T0, T2>
  T1 requests [1, 0, 2]: granted: state stays SAFE  safe sequence <T1, T3, T4, T0, T2>
  T4 requests [3, 3, 0]: must wait: resources not currently available
  T0 requests [0, 2, 0]: denied: would leave the system in an UNSAFE state
  ```
* **Say:** "Need = Max − Allocation. The safety algorithm repeatedly finds a task whose Need fits in Work, lets it finish, and adds back its allocation. If every task can finish, the state is safe and we get a safe sequence. A request is granted only if, after pretending to grant it, the state is still safe — T0's request is physically available but unsafe, so it is held back. That's the report's 'unsafe requests are held back'."
* Test: `test_bankers_safe_sequence_matches_textbook`, `test_bankers_requests`.
* ⚠️ I believe the example and these three requests match the one in Silberschatz et al. but **could not verify the page/text online**; check your copy before saying "exactly from the textbook".

### F13. Deadlock detection + circular wait reported  (rows 6, 8)
* **Status:** Verified in code · Runnable demo
* **Code:** `detect_deadlock()` l.58, `wait_for_cycle()` l.75
* **Run:** `python demo.py detect`
* **Input:** T0 holds printer & wants bay; T1 holds bay & wants printer; T2 holds a packing station and wants nothing.
* **Expected (real):**
  ```
  Detection -> DEADLOCK among T0, T1
  Four conditions: {'mutual_exclusion': True, 'hold_and_wait': True, 'no_preemption': True, 'circular_wait': True}
  Circular wait reported: T0 -> T1 -> T0
  ```
* **Say:** "T2 can finish and is not stuck. T0 and T1 each wait for what the other holds — a cycle in the wait-for graph. Only shared resources are modelled, never workers or robots as processes (report row 10)."
* Four conditions (row 7): `four_conditions()` l.141. Mutual exclusion & no-pre-emption are *true by modelling*; hold-and-wait and circular wait are *computed*.

### F14. Deadlock recovery (terminate/restart a task)  (rows 6, 7)
* **Status:** Verified in code · Runnable (same command)
* **Code:** `recover()` l.108
* **Expected (real):**
  ```
  - deadlocked: T0, T1
  - abort victim T1 (priority 4), releasing {... 'DispatchBay': 1}; task re-queued for restart
  - no deadlock remains
  ```
* **Say:** "Victim = lowest priority (largest number). Its resources are released, detection runs again, and the loop stops when no deadlock remains."

### F15. Deadlock prevention by a fixed request order  (row 7)
* **Status:** Verified in code · Runnable demo (minimal)
* **Code:** `ordered_request_ok()` l.132
* **Run:** `python demo.py prevent`
* **Expected (real):** PackingStation→LabelPrinter `ALLOWED`; DispatchBay→LabelPrinter `REJECTED (would break the order -> no circular wait)`.

### F16. Claims with **no code possible** (state these honestly)
| Claim (row) | Status |
|---|---|
| RTOS case study; database deadlock-avoidance case study (rows 6, 9, 11) | **Report claim only** — documents; show your written case studies |
| Dining Philosophers, Sleeping Barber "studied as models" (row 4) | **Report claim only** — no implementation claimed |
| Hyper-threading, thread types/models (row 4) | **Report claim only** — concept only, as the report says |
| Rate-Monotonic / EDF from Liu & Layland | **Not implemented**; report says concepts only |
| Review 1 modules still working / re-run tests (row 10) | **Evidence not found** (Review 1 code not visible) |
| Gantt chart *images*, evidence screenshots (row 9) | **Evidence not found** (terminal text Gantt provided instead) |
| "Numerical comparisons will be consolidated in the final report" (row 8) | Honest: no final numbers in the report |
| Who coded what (row 11) | **Evidence not found** — needs git commit history, which is empty |

---

## 3. Suggested 8-minute demo order

```bash
python -m unittest -v                         # 1. 19 tests pass (proof, 20 s)
python demo.py sched rr --dataset tiny-rr     # 2. RR on a hand-checkable example
python demo.py sched priority-p --dataset tiny-prio   # 3. pre-emption
python demo.py sched mlq                      # 4. queue levels
python demo.py sched mlfq                     # 5. demotion/aging
python demo.py compare --scenario starvation --aging 4   # 6. the starvation claim
python demo.py quantum                        # 7. quantum trade-off
python demo.py race                           # 8. lost update vs semaphore
python demo.py buffer                         # 9. producer-consumer
python demo.py banker                         # 10. safe sequence, grant/deny
python demo.py detect                         # 11. detection + recovery
```

---

## 4. Research-paper / source list

| # | Source | Citation verified? | Link verified? |
|---|---|---|---|
| [1] | A. Silberschatz, P. B. Galvin, G. Gagne, *Operating System Concepts*, 10th ed., Wiley, 2018 | **Verified** — matches a library catalogue record (10th ed., Wiley, 2018, xxvi + 1006 pp.) | **Verified (catalogue record only):** https://elibrary.lu.edu.ph/students/catalog/2911/ . No publisher page was verified. ISBNs differ by binding (that record: 978-1-119-32091-3; another catalogue lists 978-1-119-80036-1 for the loose-leaf), so quote the ISBN from *your own copy*. |
| [2] | C. L. Liu and J. W. Layland, "Scheduling Algorithms for Multiprogramming in a Hard-Real-Time Environment," *Journal of the ACM*, vol. 20, no. 1, pp. 46–61, Jan 1973 | **Verified** — volume, issue, pages and month match the MIT/CSAIL *Journal of the ACM* bibliography | **Verified:** bibliography page https://projects.csail.mit.edu/jacm/References/liul1973:46.html ; full-text PDF copies hosted by universities (not the publisher): https://www.cis.upenn.edu/~lee/07cis505/Lec/liu73scheduling.pdf and https://home.cs.colorado.edu/~rhan/CSCI_5573_Fall_2011/Papers/p46-liu.pdf . **DOI not verified** in this session — look it up on dl.acm.org before printing one. |

**Relevance and where each appears**

* **[1] Silberschatz et al.** — Report cited in row 3 (also named for Round Robin, multilevel queues, threads, synchronization, deadlock). *Idea used:* the textbook definitions and algorithms behind Round Robin, MLQ, MLFQ, semaphores, bounded-buffer / readers-writers, the Banker's safety and request algorithms, detection and recovery. *Code:* all of `schedulers.py`, `sync.py`, `deadlock.py`. **Not verified:** exact chapter/page for each algorithm and whether the Banker's example numbers are copied from the book — check your copy and write the page numbers on your slide. (From memory, scheduling, synchronization and deadlocks are separate chapters in the 10th ed.; confirm the numbers.)
* **[2] Liu & Layland 1973** — Report cited in row 3 for "priority-driven pre-emptive scheduling, used for the RTOS case study". *Verified from the paper text:* its algorithms are pre-emptive and priority-driven. *Idea in the paper:* fixed-priority (rate-monotonic) and deadline-driven scheduling with utilisation bounds for periodic hard-real-time tasks. *Code:* **no implementation uses it.** `priority_preemptive()` is the generic pre-emptive-priority idea, not rate-monotonic or EDF. Don't claim the code implements the paper; say it informs the RTOS case study (which is Report claim only).

No other papers are cited in the report. Nothing else was found, and none were invented.

---

## 5. Final checklist

| Claim / source | Status |
|---|---|
| Team's own code exists in GitHub repo | ❌ Evidence not found (repo empty) |
| Non-pre-emptive & pre-emptive priority | ✅ Verified in code, runnable (reference impl.) |
| Round Robin + configurable quantum | ✅ Verified, runnable, hand-checked |
| Multilevel Queue (3 queues as described) | ✅ Verified, runnable |
| MLFQ (demotion + aging) | ✅ Verified, runnable |
| Metrics (WT/TAT/RT), context switches, Gantt (text) | ✅ Verified, runnable |
| "RR & MLFQ reduce starvation" | ✅ Supported on the starvation scenario only; ❌ not shown on the main 6-task set |
| Threads / thread states | ✅ Modelled & runnable; theory topics = Report claim only |
| Race condition + semaphore | ✅ Verified, runnable |
| Bounded buffer | ✅ Verified, runnable |
| Readers-Writers | ✅ Verified, runnable (added) |
| Banker's Algorithm (not a bank account) | ✅ Verified, runnable |
| Detection, circular wait, recovery | ✅ Verified, runnable |
| Prevention by fixed order | ✅ Verified, runnable (minimal) |
| Four conditions "checked" | ✅ Two computed, two by-construction |
| RTOS & DB-deadlock case studies | 📄 Report claim only — bring your written notes |
| Dining Philosophers / Sleeping Barber / hyper-threading | 📄 Report claim only (concept) |
| Review 1 modules unchanged, Review 1 tests re-run | ❌ Evidence not found |
| Gantt chart images / screenshots | ❌ Evidence not found |
| Who implemented what (row 11) | ❌ Evidence not found (no commits) |
| Citation [1] Silberschatz | ✅ Citation verified, link = library catalogue only; chapter/page ⚠ unverified |
| Citation [2] Liu & Layland | ✅ Citation verified, link verified; DOI ⚠ unverified; not implemented in code |
