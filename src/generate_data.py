"""Generate synthetic contact-center case data.

No real client data is used. Faker produces synthetic names, phones, and emails;
case attributes are drawn from generic templates. Every row is unambiguously synthetic.
"""

from __future__ import annotations

import argparse
import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

from faker import Faker

SYMPTOM_CATEGORIES = [
    "boot_failure",
    "display_issue",
    "battery",
    "overheat",
    "noise",
    "performance",
    "connectivity",
    "physical_damage",
    "other",
]

SYMPTOM_DESCRIPTIONS = {
    "boot_failure":    "device fails to power on",
    "display_issue":   "screen flickers intermittently",
    "battery":         "battery drains rapidly",
    "overheat":        "device overheats during use",
    "noise":           "abnormal sound from speaker",
    "performance":     "system response is slow",
    "connectivity":    "wireless connection drops",
    "physical_damage": "casing is bent or cracked",
    "other":           "unspecified issue",
}

PURCHASE_SOURCES = ["official", "third_party", "unknown"]
WARRANTY_STATUSES = ["in_scope", "out_of_scope"]
ESCALATION_LEVELS = ["T1", "T2", "T3"]


def build_case(faker: Faker, index: int, base_date: datetime) -> dict:
    offset = random.randint(0, 180)
    contact_date = (base_date - timedelta(days=offset)).strftime("%Y-%m-%d")
    purchase_source = random.choice(PURCHASE_SOURCES)
    symptom = random.choice(SYMPTOM_CATEGORIES)
    return {
        "case_id":             f"CASE-{index:05d}",
        "contact_date":        contact_date,
        "customer_name":       faker.name(),
        "customer_phone":      faker.numerify("###-###-####"),
        "customer_email":      faker.email(),
        "symptom_category":    symptom,
        "symptom_description": SYMPTOM_DESCRIPTIONS[symptom],
        "purchase_source":     purchase_source,
        "warranty_status":     random.choice(WARRANTY_STATUSES),
        "third_party":         purchase_source == "third_party",
        "resolution_time":     random.randint(5, 120),
        "qa_score":            random.randint(1, 5),
        "escalation_level":    random.choice(ESCALATION_LEVELS),
        "agent_id":            f"AGENT-{random.randint(1, 30):03d}",
    }


def generate(count: int, seed: int | None) -> list[dict]:
    if seed is not None:
        random.seed(seed)
        Faker.seed(seed)
    faker = Faker("en_US")
    base_date = datetime(2026, 6, 24)
    return [build_case(faker, i, base_date) for i in range(1, count + 1)]


def write_csv(rows: list[dict], path: Path) -> None:
    if not rows:
        raise ValueError("no rows to write")
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic contact-center cases.")
    parser.add_argument("--output", type=Path, default=Path("data/synthetic/cases.csv"))
    parser.add_argument("--count",  type=int,  default=200)
    parser.add_argument("--seed",   type=int,  default=42)
    args = parser.parse_args(argv)

    rows = generate(count=args.count, seed=args.seed)
    write_csv(rows, args.output)
    print(f"[generate_data] wrote {len(rows)} synthetic cases -> {args.output}")


if __name__ == "__main__":
    main()
