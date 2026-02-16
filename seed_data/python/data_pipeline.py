from dataclasses import dataclass
from typing import Iterable

@dataclass
class Record:
    id: str
    score: float

class Transformer:
    threshold = 0.5

    def normalize(self, records: Iterable[Record]) -> list[Record]:
        return [Record(r.id, min(max(r.score, 0.0), 1.0)) for r in records]

    def filter_high(self, records: Iterable[Record]) -> list[Record]:
        return [r for r in records if r.score >= self.threshold]

class Pipeline:
    def __init__(self):
        self.transformer = Transformer()

    def run(self, rows: Iterable[Record]) -> list[Record]:
        data = self.transformer.normalize(rows)
        return self.transformer.filter_high(data)
