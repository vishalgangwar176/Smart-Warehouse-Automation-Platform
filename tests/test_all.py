"""Run:  python -m unittest -v
Expected values marked (hand) were worked out on paper, independently of the code."""
import unittest

from warehouse.models import TINY_RR, TINY_PRIO, STARVATION, SAMPLE_TASKS
from warehouse.schedulers import (round_robin, priority_preemptive, priority_non_preemptive,
                                  multilevel_queue, mlfq)
from warehouse.metrics import compute_metrics, segments
from warehouse import sync, deadlock as dl

ALLOC = [[0, 1, 0], [2, 0, 0], [3, 0, 2], [2, 1, 1], [0, 0, 2]]
MAXIM = [[7, 5, 3], [3, 2, 2], [9, 0, 2], [2, 2, 2], [4, 3, 3]]
AVAIL = [3, 3, 2]


def by_pid(tasks, ticks):
    return {r["pid"]: r for r in compute_metrics(tasks, ticks)}


class Scheduling(unittest.TestCase):
    def test_round_robin_gantt_and_metrics_hand(self):
        ticks = round_robin(TINY_RR, 2)
        self.assertEqual(segments(ticks),
                         [(0, 2, "A"), (2, 4, "B"), (4, 5, "C"), (5, 7, "A"), (7, 8, "B"), (8, 9, "A")])
        m = by_pid(TINY_RR, ticks)
        self.assertEqual((m["A"]["waiting"], m["B"]["waiting"], m["C"]["waiting"]), (4, 4, 2))
        self.assertEqual((m["A"]["turnaround"], m["B"]["turnaround"], m["C"]["turnaround"]), (9, 7, 3))
        self.assertEqual((m["A"]["response"], m["B"]["response"], m["C"]["response"]), (0, 1, 2))

    def test_preemptive_priority_hand(self):
        ticks = priority_preemptive(TINY_PRIO)
        self.assertEqual(segments(ticks), [(0, 1, "A"), (1, 3, "B"), (3, 5, "A")])

    def test_non_preemptive_priority_does_not_preempt(self):
        ticks = priority_non_preemptive(TINY_PRIO)
        self.assertEqual(segments(ticks), [(0, 3, "A"), (3, 5, "B")])

    def test_every_scheduler_runs_each_task_exactly_its_burst(self):
        for fn in (priority_non_preemptive, priority_preemptive, round_robin, multilevel_queue, mlfq):
            for tasks in (SAMPLE_TASKS, STARVATION):
                ticks = fn(tasks)
                for t in tasks:
                    self.assertEqual(ticks.count(t.pid), t.burst, (fn.__name__, t.pid))
                for t in tasks:  # nothing runs before it arrives
                    self.assertGreaterEqual(ticks.index(t.pid), t.arrival)

    def test_mlq_urgent_preempts_normal(self):
        ticks = multilevel_queue(SAMPLE_TASKS, 2)
        self.assertEqual(ticks[2:5], ["T3", "T3", "T3"])        # urgent T3 runs the moment it arrives

    def test_starvation_claim(self):
        pre = by_pid(STARVATION, priority_preemptive(STARVATION))["R1"]["waiting"]
        rr = by_pid(STARVATION, round_robin(STARVATION, 2))["R1"]["waiting"]
        fb = by_pid(STARVATION, mlfq(STARVATION, aging=4))["R1"]["waiting"]
        self.assertEqual((pre, rr, fb), (16, 2, 6))
        self.assertLess(rr, pre)
        self.assertLess(fb, pre)

    def test_quantum_large_behaves_like_fcfs(self):
        self.assertEqual(round_robin(SAMPLE_TASKS, 100), round_robin(SAMPLE_TASKS, 1000))


class Concurrency(unittest.TestCase):
    def test_race_condition_loses_updates(self):
        final, expected = sync.update_inventory(False)
        self.assertGreater(final, expected)

    def test_semaphore_keeps_count_correct(self):
        final, expected = sync.update_inventory(True)
        self.assertEqual(final, expected)

    def test_bounded_buffer(self):
        orders = [f"O{i}" for i in range(10)]
        _, consumed, mx = sync.bounded_buffer(orders, capacity=3, consumer_delay=0.005)
        self.assertEqual(consumed, orders)
        self.assertLessEqual(mx, 3)

    def test_readers_writers(self):
        _, max_r, violation = sync.readers_writers()
        self.assertGreater(max_r, 1)
        self.assertFalse(violation)

    def test_thread_states(self):
        threads, shared = sync.run_task_threads()
        self.assertEqual([s.value for s in threads[0].history],
                         ["NEW", "READY", "RUNNING", "TERMINATED"])
        self.assertIn(sync.State.WAITING, threads[1].history)
        self.assertEqual(len(shared["log"]), 3)


class Deadlock(unittest.TestCase):
    def test_bankers_safe_sequence_matches_textbook(self):
        safe, seq = dl.is_safe(AVAIL, MAXIM, ALLOC)
        self.assertTrue(safe)
        self.assertEqual(seq, [1, 3, 4, 0, 2])                   # <P1,P3,P4,P0,P2>

    def test_bankers_requests(self):
        ok, _, avail, alloc, _ = dl.request_resources(1, [1, 0, 2], AVAIL, MAXIM, ALLOC)
        self.assertTrue(ok)
        ok, why, *_ = dl.request_resources(4, [3, 3, 0], avail, MAXIM, alloc)
        self.assertFalse(ok); self.assertIn("not currently available", why)
        ok, why, *_ = dl.request_resources(0, [0, 2, 0], avail, MAXIM, alloc)
        self.assertFalse(ok); self.assertIn("UNSAFE", why)

    def test_request_beyond_max_rejected(self):
        ok, why, *_ = dl.request_resources(1, [9, 0, 0], AVAIL, MAXIM, ALLOC)
        self.assertFalse(ok); self.assertIn("maximum", why)

    def test_detection_cycle_and_recovery(self):
        alloc = [[0, 1, 0], [0, 0, 1], [1, 0, 0]]
        req = [[0, 0, 1], [0, 1, 0], [0, 0, 0]]
        self.assertEqual(dl.detect_deadlock([0, 0, 0], alloc, req), [0, 1])
        self.assertEqual(dl.wait_for_cycle(alloc, req, [0, 0, 0]), [0, 1, 0])
        steps, victims = dl.recover(["T0", "T1", "T2"], [2, 4, 3], [0, 0, 0], alloc, req)
        self.assertEqual(victims, ["T1"])

    def test_four_conditions(self):
        alloc = [[0, 1, 0], [0, 0, 1], [1, 0, 0]]
        req = [[0, 0, 1], [0, 1, 0], [0, 0, 0]]
        c = dl.four_conditions(alloc, req, [0, 0, 0])
        self.assertTrue(all(c.values()))
        c2 = dl.four_conditions(ALLOC, [[0, 0, 0]] * 5, AVAIL)
        self.assertFalse(c2["circular_wait"]); self.assertFalse(c2["hold_and_wait"])

    def test_no_false_deadlock(self):
        self.assertEqual(dl.detect_deadlock([3, 3, 2], ALLOC, [[0, 0, 0]] * 5), [])

    def test_prevention_order(self):
        self.assertTrue(dl.ordered_request_ok(["PackingStation"], "LabelPrinter"))
        self.assertFalse(dl.ordered_request_ok(["DispatchBay"], "LabelPrinter"))


if __name__ == "__main__":
    unittest.main()
