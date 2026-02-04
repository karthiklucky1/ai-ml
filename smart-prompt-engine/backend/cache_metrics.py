from __future__ import annotations

from dataclasses import dataclass, asdict, field
from typing import Dict
import time


@dataclass
class CacheStats:
    name: str
    hits: int = 0
    misses: int = 0
    sets: int = 0
    evictions: int = 0
    last_reset_ts: float = field(default_factory=time.time)

    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return (self.hits / total) if total else 0.0

    def to_dict(self) -> Dict:
        d = asdict(self)
        d["hit_rate"] = self.hit_rate()
        d["uptime_seconds"] = int(time.time() - self.last_reset_ts)
        return d


def reset_stats(stats: CacheStats) -> None:
    stats.hits = 0
    stats.misses = 0
    stats.sets = 0
    stats.evictions = 0
    stats.last_reset_ts = time.time()
