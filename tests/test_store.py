import json

import pytest

from surfacediff.normalize import Asset
from surfacediff.store import latest_pair, list_snapshots, load, prune, snap


def make(n=3):
    return [Asset("host", f"host{i}.example.com") for i in range(n)]


def test_prune_keeps_newest_and_deletes_rest(tmp_path):
    for n in (1, 2, 3, 4, 5):
        snap(str(tmp_path), "subs", make(n))
    deleted, kept = prune(str(tmp_path), "subs", 2)
    assert len(deleted) == 3
    remaining = list_snapshots(str(tmp_path), "subs")
    assert len(remaining) == 2
    assert kept == remaining[-1]


def test_prune_keeps_newest_data_not_oldest(tmp_path):
    """The surviving snapshots must be the newest ones, by asset count."""
    for n in (1, 2, 3, 4, 5):
        snap(str(tmp_path), "subs", make(n))
    prune(str(tmp_path), "subs", 2)
    data = load(str(tmp_path), "subs", "current")
    assert len(data["records"]) == 5


def test_prune_repoints_current_so_diff_still_works(tmp_path):
    for n in (1, 2, 3, 4):
        snap(str(tmp_path), "subs", make(n))
    prune(str(tmp_path), "subs", 1)
    ptr = (tmp_path / "subs" / "current").read_text().strip()
    assert (tmp_path / "subs" / ptr).exists(), "pointer must not dangle"
    assert len(load(str(tmp_path), "subs", "current")["records"]) == 4


def test_prune_refuses_keep_below_one(tmp_path):
    for n in (1, 2, 3):
        snap(str(tmp_path), "subs", make(n))
    with pytest.raises(ValueError):
        prune(str(tmp_path), "subs", 0)
    assert len(list_snapshots(str(tmp_path), "subs")) == 3, "nothing may be deleted"


def test_prune_keeps_all_when_keep_exceeds_count(tmp_path):
    for n in (1, 2):
        snap(str(tmp_path), "subs", make(n))
    deleted, _ = prune(str(tmp_path), "subs", 99)
    assert deleted == []
    assert len(list_snapshots(str(tmp_path), "subs")) == 2


def test_prune_on_empty_label_errors(tmp_path):
    with pytest.raises(ValueError):
        prune(str(tmp_path), "nothing-here", 5)


def test_snap_writes_pointer_and_meta(tmp_path):
    p = snap(str(tmp_path), "subs", make(), tags={"source": "subfinder"})
    ptr = (tmp_path / "subs" / "current").read_text()
    assert p.name == ptr and ptr.endswith(".jsonl")
    first = json.loads(p.read_text().splitlines()[0])
    assert "_meta" in first and first["_meta"]["tags"]["source"] == "subfinder"
    assert first["_meta"]["format"] == 1


def test_records_sorted_by_key(tmp_path):
    snap(str(tmp_path), "subs", make())
    data = load(str(tmp_path), "subs", "current")
    keys = list(data["records"])
    assert keys == sorted(keys)


def test_load_by_timestamp_prefix(tmp_path):
    p1 = snap(str(tmp_path), "subs", make(1))
    p2 = snap(str(tmp_path), "subs", make(3))
    ref = p2.stem[:15]
    data = load(str(tmp_path), "subs", ref)
    assert len(data["records"]) == 3


def test_latest_pair_uses_two_most_recent(tmp_path):
    snap(str(tmp_path), "subs", make(1))
    snap(str(tmp_path), "subs", make(2))
    snap(str(tmp_path), "subs", make(4))
    old, new = latest_pair(str(tmp_path), "subs", None)
    assert len(old["records"]) == 2 and len(new["records"]) == 4
    assert len(list_snapshots(str(tmp_path), "subs")) == 3


def test_invalid_label_refused(tmp_path):
    with pytest.raises(ValueError):
        snap(str(tmp_path), "../evil", [])
