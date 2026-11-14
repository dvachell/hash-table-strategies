"""Class decorator that adds probe/collision statistics to a hash table
without touching the algorithm code."""
import functools


class Stats:
    """Counters for one table. `history` holds per-operation deltas."""

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.operations = 0
        self.probes = 0
        self.collisions = 0
        self.rehashes = 0
        self.structural_events = 0
        self.history = []


def profile_hashing(cls):
    """Wrap the table's methods to count:
    - probes and collisions (every inspect() call),
    - rehashes,
    - structural events (methods listed in cls.profiled_events),
    and record per-operation deltas for insert/get/remove."""
    required = ("insert", "get", "remove", "inspect", "rehash") + tuple(getattr(cls, "profiled_events", ()))
    for name in required:
        if not callable(getattr(cls, name, None)):
            raise TypeError(f"{cls.__name__}: missing method {name}")

    cls.__init__ = wrap_init(cls.__init__)
    cls.reset_stats = reset_stats
    cls.inspect = wrap_inspect(cls.inspect)
    cls.rehash = wrap_counter(cls.rehash, "rehashes")
    for name in cls.profiled_events:
        setattr(cls, name, wrap_counter(getattr(cls, name), "structural_events"))
    for name in ("insert", "get", "remove"):
        setattr(cls, name, wrap_operation(getattr(cls, name)))
    return cls


def reset_stats(self) -> None:
    self.stats.reset()


def wrap_init(method):
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        self.stats = Stats()
        method(self, *args, **kwargs)
    return wrapper


def wrap_inspect(method):
    @functools.wraps(method)
    def wrapper(self, index, key):
        state = method(self, index, key)
        self.stats.probes += 1
        if state == "other":
            self.stats.collisions += 1
        return state
    return wrapper


def wrap_counter(method, counter: str):
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        setattr(self.stats, counter, getattr(self.stats, counter) + 1)
        return method(self, *args, **kwargs)
    return wrapper


def wrap_operation(method):
    @functools.wraps(method)
    def wrapper(self, key, *args):
        stats = self.stats
        probes, collisions, events = stats.probes, stats.collisions, stats.structural_events
        result = method(self, key, *args)
        stats.operations += 1
        stats.history.append({
            "operation": method.__name__,
            "key": key,
            "probes": stats.probes - probes,
            "collisions": stats.collisions - collisions,
            "structural_events": stats.structural_events - events,
        })
        return result
    return wrapper
