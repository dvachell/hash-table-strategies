"""Console demo: config validation, the Robin Hood table, collected
statistics, and an average-probes comparison of both strategies."""

from config import HashConfig, generate_collision_keys
from hash_tables import HashTableMeta, create_hash_table


def run_workload(table, keys: list[int]) -> None:
    """Same operation mix for every table: inserts, hits, a miss, a delete."""
    for key in keys:
        table.insert(key, f"v{key}")
    table.get(keys[0])
    table.get(keys[-1])
    table.get(9999)
    table.remove(keys[1])
    table.insert(54, "v54")


# Config validation and collision key generator
cfg = HashConfig(strategy="robin_hood", capacity=13, max_load=0.5)
print(cfg)
keys = generate_collision_keys(6, 13, 2, 7)
print(keys)
try:
    cfg.capacity = 12
except ValueError as e:
    print(e)

# Registry and basic Robin Hood operations
print(list(HashTableMeta.registry))
table = create_hash_table(HashConfig(strategy="robin_hood", capacity=13, max_load=0.5))
for key in (0, 1, 13, 26):
    table.insert(key, f"v{key}")
print(table.get(26), table.remove(13))
table.insert(39, "v39")
print(table.snapshot())

# Statistics collected by the profiling decorator
table = create_hash_table(HashConfig(strategy="robin_hood", capacity=13, max_load=0.5))
run_workload(table, keys)
stats = table.stats
print(
    f"operations={stats.operations} probes={stats.probes} collisions={stats.collisions} "
    f"rehashes={stats.rehashes} structural_events={stats.structural_events}"
)
print([record["probes"] for record in stats.history])

# Robin Hood vs double hashing on the same workload
for strategy in ("robin_hood", "double_hashing"):
    table = create_hash_table(HashConfig(strategy=strategy, capacity=13, max_load=0.5))
    run_workload(table, keys)
    print(f"avg_probes_{strategy}={table.stats.probes / table.stats.operations:.2f}")
