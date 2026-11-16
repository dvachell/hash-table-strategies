import pytest

from config import HashConfig, generate_collision_keys
from hash_tables import HashTable, HashTableMeta, RobinHoodTable, create_hash_table


def make_table(capacity: int = 7, max_load: float = 0.5):
    return create_hash_table(
        HashConfig(strategy="robin_hood", capacity=capacity, max_load=max_load)
    )


def test_config_and_generator():
    """Descriptors reject bad values, also after construction; the generator is deterministic."""
    with pytest.raises(TypeError):
        HashConfig(capacity=True)
    with pytest.raises(ValueError):
        HashConfig(capacity=12)
    with pytest.raises(ValueError):
        HashConfig(max_load=1.5)
    with pytest.raises(ValueError):
        HashConfig(strategy="unknown")

    cfg = HashConfig(capacity=13)
    with pytest.raises(ValueError):
        cfg.capacity = 12

    assert generate_collision_keys(6, 13, 2, 7) == generate_collision_keys(6, 13, 2, 7)


def test_interface_and_resize():
    """Insert/update/get/remove behave like a dict; the table grows past max_load."""
    table = make_table()
    table.insert(1, "a")
    table.insert(1, "b")
    assert len(table) == 1
    assert table.get(1) == "b"
    assert table.get(2) is None
    assert table.remove(1) is True
    assert table.remove(1) is False

    table = make_table(max_load=0.3)
    for key in range(10):
        table.insert(key, f"v{key}")
    assert table.capacity > 7
    assert all(table.get(key) == f"v{key}" for key in range(10))


def test_meta_and_profiling():
    """Incomplete classes are rejected at definition time; per-operation stats add up."""
    assert HashTableMeta.registry["robin_hood"] is RobinHoodTable

    with pytest.raises(TypeError):

        class Broken(HashTable):
            strategy = "broken"
            max_supported_load = 0.5
            profiled_events = ()

    assert "broken" not in HashTableMeta.registry

    table = make_table()
    for key in (0, 7, 14):
        table.insert(key, "x")
    assert sum(record["probes"] for record in table.stats.history) == table.stats.probes

    table.reset_stats()
    assert table.stats.probes == 0
    assert table.stats.operations == 0


def test_robin_hood_swap_and_backward_shift():
    """Robin Hood: a real swap on insert, DIB decreased by backward shift on remove."""
    table = make_table()
    for key in (0, 1, 7):
        table.insert(key, "x")
    assert table.snapshot()[:3] == ((0, 0), (7, 1), (1, 1))

    table.remove(7)
    assert table.snapshot()[:3] == ((0, 0), (1, 0), None)
