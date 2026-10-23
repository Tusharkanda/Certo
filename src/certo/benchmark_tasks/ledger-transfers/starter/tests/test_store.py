from datetime import date

from ledger import store
from tests.helpers import tx


def test_save_and_load_round_trip(tmp_path):
    path = tmp_path / "ledger.jsonl"
    original = [tx("Shop", "-10.50", category="groceries"), tx("Pay", 100, category="income")]
    store.save(path, original)
    assert store.load(path) == original


def test_load_a_missing_store_is_empty(tmp_path):
    assert store.load(tmp_path / "none.jsonl") == []


def test_merge_adds_only_new_transactions_sorted_by_date():
    old = [tx("A", -1, day=date(2025, 11, 5))]
    new = [tx("A", -1, day=date(2025, 11, 5)), tx("B", -2, day=date(2025, 11, 1))]
    merged = store.merge(old, new)
    assert [t.description for t in merged] == ["B", "A"]
