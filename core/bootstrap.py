"""One-time initialisation on app start: DB schema, card seeding, gate refresh."""
from __future__ import annotations

import hashlib

from core import curriculum, db


def _card_id(module_id: str, front: str) -> str:
    return module_id + ":" + hashlib.sha1(front.encode()).hexdigest()[:10]


def seed_cards() -> None:
    existing = {r["card_id"] for r in db.query("SELECT card_id FROM cards")}
    with db.conn() as c:
        for m in curriculum.built_modules():
            for card in m["cards"]:
                cid = _card_id(m["id"], card["front"])
                if cid in existing:
                    continue
                c.execute(
                    "INSERT INTO cards(card_id,module_id,front,back,kind,due) VALUES(?,?,?,?,?,?)",
                    (cid, m["id"], card["front"], card["back"], card.get("kind", "definition"), db.today()),
                )


def init() -> None:
    db.init_db()
    seed_cards()
    curriculum.refresh_gates()
