"""Common hash table base, metaclass registry, factory,
and the Robin Hood open-addressing table."""

from typing import ClassVar

from config import HashConfig, next_prime
from hash_profiling import profile_hashing


class Entry:
    """A stored key/value pair. `dib` is the distance from the key's
    initial bucket (its home slot), used by Robin Hood hashing."""

    def __init__(self, key: int, value, dib: int = 0) -> None:
        self.key = key
        self.value = value
        self.dib = dib


class HashTableMeta(type):
    """Checks at class-definition time that a concrete table implements
    the full interface, and registers it under its `strategy` name."""

    strategy: str
    registry: ClassVar[dict[str, type]] = {}
    required = (
        "strategy",
        "max_supported_load",
        "profiled_events",
        "insert",
        "get",
        "remove",
        "inspect",
        "rehash",
    )

    def __new__(mcls, name, bases, namespace, abstract=False):
        cls = super().__new__(mcls, name, bases, namespace)
        if abstract:
            return cls
        for attr in mcls.required + tuple(getattr(cls, "profiled_events", ())):
            if not hasattr(cls, attr):
                raise TypeError(f"{name}: missing required member {attr}")
        strategy = cls.strategy
        if strategy in mcls.registry:
            raise TypeError(f"strategy {strategy} is already registered")
        mcls.registry[strategy] = cls
        return cls


class HashTable(metaclass=HashTableMeta, abstract=True):
    """State and helpers shared by all open-addressing tables."""

    def __init__(self, config: HashConfig) -> None:
        self.capacity = config.capacity
        self.max_load = config.max_load
        self.size = 0
        self._slots: list = [None] * self.capacity

    def __len__(self) -> int:
        return self.size

    @property
    def load_factor(self) -> float:
        return self.size / self.capacity

    def needs_rehash(self) -> bool:
        """True if adding one more key would exceed max_load."""
        return (self.size + 1) / self.capacity > self.max_load

    def snapshot(self) -> tuple:
        """Read-only view of the slots as (key, dib) or None."""
        return tuple(
            None if entry is None else (entry.key, entry.dib) for entry in self._slots
        )


def create_hash_table(config: HashConfig):
    """Build the table registered for config.strategy."""
    cls = HashTableMeta.registry.get(config.strategy)
    if cls is None:
        raise ValueError(f"no table class for strategy {config.strategy}")
    if config.max_load > cls.max_supported_load:
        raise ValueError(
            f"max_load {config.max_load} > {cls.max_supported_load} for {config.strategy}"
        )
    return cls(config)


@profile_hashing
class RobinHoodTable(HashTable):
    """Linear probing where a key that is further from its home slot
    takes the place of a key that is closer ("rob the rich"). This keeps
    probe lengths even. Deletion uses backward shift, so no tombstones."""

    strategy = "robin_hood"
    max_supported_load = 0.85
    profiled_events = ("_swap", "_shift")

    def inspect(self, index: int, key: int) -> str:
        """Classify a slot as 'empty', 'same' (holds key) or 'other'."""
        entry = self._slots[index]
        if entry is None:
            return "empty"
        if entry.key == key:
            return "same"
        return "other"

    def insert(self, key: int, value) -> None:
        self._insert(Entry(key, value))

    def _insert(self, incoming: Entry) -> None:
        index = incoming.key % self.capacity
        is_new = False
        for _ in range(self.capacity):
            state = self.inspect(index, incoming.key)
            if state == "same":
                self._slots[index].value = incoming.value
                return
            if state == "empty" or incoming.dib > self._slots[index].dib:
                # from here on the key is surely not in the table
                if not is_new:
                    is_new = True
                    if self.needs_rehash():
                        self.rehash(next_prime(2 * self.capacity))
                        return self._insert(Entry(incoming.key, incoming.value))
                if state == "empty":
                    self._slots[index] = incoming
                    self.size += 1
                    return
                # the resident is closer to home: take its slot, carry it on
                incoming = self._swap(index, incoming)
            incoming.dib += 1
            index = (index + 1) % self.capacity
        raise RuntimeError("no free slot")

    def _swap(self, index: int, incoming: Entry) -> Entry:
        displaced = self._slots[index]
        self._slots[index] = incoming
        return displaced

    def _find(self, key: int) -> int | None:
        index = key % self.capacity
        for distance in range(self.capacity):
            state = self.inspect(index, key)
            if state == "empty":
                return None
            if state == "same":
                return index
            # if the key were here, it would have displaced this entry
            if self._slots[index].dib < distance:
                return None
            index = (index + 1) % self.capacity
        return None

    def get(self, key: int):
        index = self._find(key)
        if index is None:
            return None
        return self._slots[index].value

    def remove(self, key: int) -> bool:
        index = self._find(key)
        if index is None:
            return False
        # backward shift: pull following entries one slot closer to home
        # until an empty slot or an entry already at home (dib == 0)
        for _ in range(self.capacity):
            next_index = (index + 1) % self.capacity
            entry = self._slots[next_index]
            if entry is None or entry.dib == 0:
                break
            self._shift(next_index, index)
            index = next_index
        self._slots[index] = None
        self.size -= 1
        return True

    def _shift(self, source: int, target: int) -> None:
        entry = self._slots[source]
        entry.dib -= 1
        self._slots[target] = entry

    def rehash(self, new_capacity: int) -> None:
        """Reinsert all entries into a table of new_capacity."""
        entries = [entry for entry in self._slots if entry is not None]
        self.capacity = new_capacity
        self._slots = [None] * new_capacity
        self.size = 0
        for entry in entries:
            self._insert(Entry(entry.key, entry.value))
