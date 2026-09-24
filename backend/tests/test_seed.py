"""种子核对：春茶-A 通过、夏茶-C 不通过，任一都不得被翻转。"""

import seed
from conftest import FakeDB


def test_seed_rows_keep_their_verdicts(monkeypatch):
    fake = FakeDB()
    monkeypatch.setattr(seed, "connect", fake.connect)

    seed.main()

    by_lot = {r["lot"]: r for r in fake.rows}
    assert by_lot["春茶-A"]["verdict"] == "通过"
    assert by_lot["春茶-A"]["note"] == "加权分达到放行线"
    assert by_lot["春茶-A"]["score"] == 7.8

    assert by_lot["夏茶-C"]["verdict"] == "不通过"
    assert by_lot["夏茶-C"]["note"] == "加权分低于放行线"
    assert by_lot["夏茶-C"]["score"] == 4.7
