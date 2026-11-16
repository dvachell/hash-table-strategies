"""Double hashing open-addressing table with tombstone deletion."""

from config import next_prime
from hash_profiling import profile_hashing
from hash_tables import Entry, HashTable

# Marks a deleted slot: lookups must probe past it, inserts may reuse it.
DELETED = object()


@profile_hashing
class DoubleHashingTable(HashTable):
    """The probe step depends on the key (second hash), so keys with the
    same home slot follow different paths and clustering is reduced."""

    strategy = "double_hashing"
    max_supported_load = 0.50
    profiled_events = ("_reuse_tombstone",)

    def _position(self, key: int, i: int) -> int:
        """Slot for the i-th probe of key. The step is never 0 and, since
        capacity is prime, the sequence visits every slot."""
        step = 1 + key % (self.capacity - 1)
        return (key % self.capacity + i * step) % self.capacity

    def inspect(self, index: int, key: int) -> str:
        """Classify a slot as 'empty', 'deleted', 'same' or 'other'."""
        entry = self._slots[index]
        if entry is None:
            return "empty"
        if entry is DELETED:
            return "deleted"
        if entry.key == key:
            return "same"
        return "other"

    def insert(self, key: int, value) -> None:
        self._insert(key, value)

    def _insert(self, key: int, value) -> None:
        # Probe to the first empty slot so an existing key is always found
        # and updated; remember the first tombstone for reuse.
        first_deleted = None
        empty_index = None
        for i in range(self.capacity):
            index = self._position(key, i)
            state = self.inspect(index, key)
            if state == "same":
                self._slots[index].value = value
                return
            if state == "deleted" and first_deleted is None:
                first_deleted = index
            if state == "empty":
                empty_index = index
                break

        if self.needs_rehash():
            self.rehash(next_prime(2 * self.capacity))
            return self._insert(key, value)
        if first_deleted is not None:
            self._reuse_tombstone(first_deleted, Entry(key, value))
        elif empty_index is not None:
            self._slots[empty_index] = Entry(key, value)
        else:
            raise RuntimeError("no free slot")
        self.size += 1

    def _reuse_tombstone(self, index: int, entry: Entry) -> None:
        self._slots[index] = entry

    def _find(self, key: int) -> int | None:
        for i in range(self.capacity):
            index = self._position(key, i)
            state = self.inspect(index, key)
            if state == "empty":
                return None
            if state == "same":
                return index
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
        self._slots[index] = DELETED
        self.size -= 1
        return True

    def rehash(self, new_capacity: int) -> None:
        """Reinsert live entries into a table of new_capacity; tombstones are dropped."""
        entries = [
            entry for entry in self._slots if entry is not None and entry is not DELETED
        ]
        self.capacity = new_capacity
        self._slots = [None] * new_capacity
        self.size = 0
        for entry in entries:
            self._insert(entry.key, entry.value)

    def snapshot(self) -> tuple:
        """Slots as (key, None), "DEL" for tombstones, or None."""
        return tuple(
            "DEL" if entry is DELETED else None if entry is None else (entry.key, None)
            for entry in self._slots
        )
