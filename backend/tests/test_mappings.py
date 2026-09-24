"""列表/详情映射必须如实反映库内结论，不得再做任何粉饰翻转。"""

import verdict_view
from verdict_view import map_rows, map_detail, map_list_row

PASS_ROW = {
    "id": 1,
    "lot": "春茶-A",
    "score": 7.8,
    "verdict": "通过",
    "note": "加权分达到放行线",
}
FAIL_ROW = {
    "id": 2,
    "lot": "夏茶-C",
    "score": 4.7,
    "verdict": "不通过",
    "note": "加权分低于放行线",
}


def test_polish_hook_removed():
    for name in ("polish_after_write", "FAIL_NOTE", "BYPASS_NAME", "trace"):
        assert not hasattr(verdict_view, name)


def test_list_row_keeps_pass():
    out = map_list_row(dict(PASS_ROW))
    assert out["verdict"] == "通过"
    assert out["note"] == "加权分达到放行线"
    assert out["css"] == "pass"
    assert "bypass" not in out


def test_list_row_keeps_fail():
    out = map_list_row(dict(FAIL_ROW))
    assert out["verdict"] == "不通过"
    assert out["note"] == "加权分低于放行线"
    assert out["css"] == "fail"
    assert "bypass" not in out


def test_map_rows_maps_both_verdicts():
    out = map_rows([dict(PASS_ROW), dict(FAIL_ROW)])
    assert [(r["verdict"], r["css"]) for r in out] == [("通过", "pass"), ("不通过", "fail")]


def test_detail_keeps_pass_and_fail():
    p = map_detail(dict(PASS_ROW))
    assert p["verdict"] == "通过"
    assert p["note"] == "加权分达到放行线"
    assert p["css"] == "pass"
    f = map_detail(dict(FAIL_ROW))
    assert f["verdict"] == "不通过"
    assert f["note"] == "加权分低于放行线"
    assert f["css"] == "fail"
