"""Hash table configuration validated by descriptors, plus a key generator
for building deterministic collision scenarios."""
import random
from typing import Any


class ValidatedField:
    """Base descriptor: validates the value on every assignment
    and stores it in a private instance attribute."""

    def __set_name__(self, owner: type, name: str) -> None:
        self.public_name = name
        self.private_name = "_" + name

    def __get__(self, obj, objtype=None) -> Any:
        if obj is None:
            return self
        return getattr(obj, self.private_name)

    def __set__(self, obj, value) -> None:
        # bool is a subclass of int, so it has to be rejected explicitly
        if isinstance(value, bool):
            raise TypeError(f"{self.public_name}: bool is not a valid type")
        self.validate(value)
        setattr(obj, self.private_name, value)

    def validate(self, value) -> None:
        raise NotImplementedError


class PrimeCapacity(ValidatedField):
    """A prime integer, at least min_value."""

    def __init__(self, min_value: int = 7) -> None:
        self.min_value = min_value

    def validate(self, value) -> None:
        if not isinstance(value, int):
            raise TypeError(f"{self.public_name} must be int, got {type(value).__name__}")
        if value < self.min_value:
            raise ValueError(f"{self.public_name} must be >= {self.min_value}, got {value}")
        if not is_prime(value):
            raise ValueError(f"{self.public_name} must be a prime number, got {value}")


class OpenUnitFloat(ValidatedField):
    """A real number in the open interval (0, 1)."""

    def validate(self, value) -> None:
        if not isinstance(value, (int, float)):
            raise TypeError(f"{self.public_name} must be a number, got {type(value).__name__}")
        if not 0 < value < 1:
            raise ValueError(f"{self.public_name} must be in (0, 1), got {value}")


class Choice(ValidatedField):
    """One of the allowed strings."""

    def __init__(self, *choices: str) -> None:
        self.choices = choices

    def validate(self, value) -> None:
        if not isinstance(value, str):
            raise TypeError(f"{self.public_name} must be str, got {type(value).__name__}")
        if value not in self.choices:
            raise ValueError(f"{self.public_name} must be one of {self.choices}, got {value!r}")


class HashConfig:
    """Hash table settings. Every field is validated on assignment,
    including changes after construction."""

    capacity = PrimeCapacity(min_value=7)
    max_load = OpenUnitFloat()
    strategy = Choice("robin_hood", "double_hashing")

    def __init__(self, capacity: int = 11, max_load: float = 0.75,
                 strategy: str = "robin_hood") -> None:
        self.capacity = capacity
        self.max_load = max_load
        self.strategy = strategy

    def __repr__(self) -> str:
        return f"strategy={self.strategy}, capacity={self.capacity}, max_load={self.max_load:.2f}"


def is_prime(n: int) -> bool:
    """Trial division by odd numbers up to sqrt(n)."""
    if n < 2:
        return False
    if n < 4:
        return True
    if n % 2 == 0:
        return False
    i = 3
    while i * i <= n:
        if n % i == 0:
            return False
        i += 2
    return True


def next_prime(n: int) -> int:
    """Smallest prime >= n."""
    n = max(n, 2)
    while not is_prime(n):
        n += 1
    return n


def generate_collision_keys(count: int, capacity: int, groups: int, seed: int) -> list[int]:
    """Deterministically generate `count` distinct keys that map to only
    `groups` home positions (k % capacity), to force collisions."""
    if count < 1:
        raise ValueError("count must be >= 1")
    if groups < 1:
        raise ValueError("groups must be >= 1")
    if groups > count:
        raise ValueError("groups cannot be greater than count")
    if groups > capacity:
        raise ValueError("groups cannot be greater than capacity")

    rng = random.Random(seed)
    residues = rng.sample(range(capacity), groups)

    keys = []
    for i in range(count):
        residue = residues[i % groups]          # cycle through the residues
        multiple = i // groups + 1              # while the multiple keeps growing
        keys.append(residue + multiple * capacity)

    rng.shuffle(keys)
    return keys
