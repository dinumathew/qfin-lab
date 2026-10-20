"""SM-2 spaced-repetition scheduler (Wozniak 1990), as used by SuperMemo 2 and Anki's ancestor.

quality q in 0..5:
  5 perfect, 4 correct after hesitation, 3 correct with serious difficulty,
  2 wrong but answer felt familiar, 1 wrong, 0 blackout.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta


@dataclass
class CardState:
    easiness: float = 2.5
    interval: int = 0
    repetitions: int = 0
    lapses: int = 0


def review(state: CardState, quality: int, on: date | None = None) -> tuple[CardState, date]:
    """Return the new state and the next due date."""
    if not 0 <= quality <= 5:
        raise ValueError("quality must be 0..5")
    on = on or date.today()
    ef, n, interval, lapses = state.easiness, state.repetitions, state.interval, state.lapses
    if quality < 3:
        n = 0
        interval = 1
        lapses += 1
    else:
        if n == 0:
            interval = 1
        elif n == 1:
            interval = 6
        else:
            interval = round(interval * ef)
        n += 1
    ef = ef + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    ef = max(1.3, ef)
    new = CardState(easiness=round(ef, 4), interval=int(interval), repetitions=n, lapses=lapses)
    return new, on + timedelta(days=int(interval))
