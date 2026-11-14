"""Plot a small Robin Hood table step by step: slot contents (key / DIB)
after each operation, and probes/collisions per operation."""
from pathlib import Path
import matplotlib.pyplot as plt
from config import HashConfig, generate_collision_keys
from hash_tables import create_hash_table

CHART_PATH = Path(__file__).parent / "robin_hood_trace.png"


if __name__ == "__main__":
    table = create_hash_table(HashConfig(strategy="robin_hood", capacity=13, max_load=0.5))
    keys = generate_collision_keys(6, 13, 2, 7)
    snapshots = []
    for key in keys:
        table.insert(key, f"v{key}")
        snapshots.append(table.snapshot())
    table.remove(keys[1])
    snapshots.append(table.snapshot())
    table.insert(54, "v54")
    snapshots.append(table.snapshot())

    history = table.stats.history
    probes = [record["probes"] for record in history]
    collisions = [record["collisions"] for record in history]
    events = [i for i, record in enumerate(history) if record["structural_events"] > 0]

    fig, (ax_slots, ax_probes) = plt.subplots(1, 2, figsize=(12, 5))
    fig.suptitle(table.strategy)

    for row, snapshot in enumerate(snapshots):
        for col, slot in enumerate(snapshot):
            if slot is not None:
                ax_slots.text(col, row, f"{slot[0]}\n{slot[1]}", ha="center", va="center")
    ax_slots.set_xlim(-1, table.capacity)
    ax_slots.set_ylim(len(snapshots), -1)
    ax_slots.set_xlabel("Slot index")
    ax_slots.set_ylabel("Operation number")

    ax_probes.plot(probes, label="probes")
    ax_probes.plot(collisions, label="collisions")
    ax_probes.scatter(events, [probes[i] for i in events], label="structural event")
    ax_probes.set_xlabel("Operation number")
    ax_probes.set_ylabel("Count")
    ax_probes.legend()

    fig.savefig(CHART_PATH)
    print(f"Chart saved: {CHART_PATH.name}")
    plt.show()
