# Smart Warehouse Automation Platform (OS simulation)

Warehouse tasks run as "processes" in an OS simulation: Priority (pre-emptive / non-pre-emptive),
Round Robin, Multilevel Queue, Multilevel Feedback Queue, semaphore synchronization
(race condition, bounded buffer, readers-writers), thread-state model, and deadlock handling
(Banker's Algorithm, detection, recovery, prevention). Python 3.8+, standard library only.

    python -m unittest -v        # 19 tests
    python demo.py --help        # live demo commands

See **EVIDENCE_GUIDE.md** for file/line locations, commands, expected outputs and sources.
