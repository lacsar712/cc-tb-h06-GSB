"""通过 / 不通过核对用例。

覆盖三处曾经挂粉饰钩子的位置：
1. 落库后置处理 —— 库内 verdict/note 必须与 rules.weigh 一致，且无 UPDATE 改写；
2. 列表文案映射 —— 列表行结论、说明、颜色与库内一致；
3. 详情说明拼装 —— 详情页结论、说明、颜色与库内一致。

另外核对夏茶-C 不通过种子不被误改，以及旁路模块已彻底移除。
"""

import os
import re

import pytest

import app as app_module
import rules
import seed
from conftest import FakeConn

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ---------- rules.weigh 判定本身 ----------

def test_weigh_pass_and_fail():
    verdict, note, score = rules.weigh(8, 8, 7)
    assert (verdict, note) == ("通过", "加权分达到放行线")
    assert score == 7.8

    verdict, note, score = rules.weigh(5, 4, 6)
    assert (verdict, note) == ("不通过", "加权分低于放行线")
    assert score == 4.7


def test_weigh_threshold_is_inclusive():
    # 7 分整应判通过，杜绝边界被改判。
    verdict, _, score = rules.weigh(7, 7, 7)
    assert score == 7.0
    assert verdict == "通过"


# ---------- 落库：通过 ----------

def test_pass_cup_persisted_as_pass(writer_client):
    client, conn = writer_client
    resp = client.post(
        "/cuppings",
        data={"lot": "春茶甲", "aroma": 8, "taste": 8, "liquor": 7},
        headers={"HX-Request": "true"},
    )
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)

    # 库内结论必须是通过，说明句保持通过口径。
    row = conn.table[0]
    assert row["verdict"] == "通过"
    assert row["note"] == "加权分达到放行线"
    assert row["score"] == 7.8

    # 落库后不得有任何 UPDATE 改写。
    assert conn.recorder["updates"] == []

    # 新行列表色为 pass，文案不被刷成不通过。
    assert 'class="pass">通过' in html
    assert "不通过" not in html
    assert "加权分低于放行线" not in html


# ---------- 落库：不通过（夏茶丙） ----------

def test_fail_cup_persisted_as_fail(writer_client):
    client, conn = writer_client
    resp = client.post(
        "/cuppings",
        data={"lot": "夏茶丙", "aroma": 5, "taste": 4, "liquor": 6},
        headers={"HX-Request": "true"},
    )
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)

    # 不通过种子同样必须原样落库，不可被任何旁路误改。
    row = conn.table[0]
    assert row["lot"] == "夏茶丙"
    assert row["verdict"] == "不通过"
    assert row["note"] == "加权分低于放行线"
    assert row["score"] == 4.7
    assert conn.recorder["updates"] == []

    # 列表色为 fail，不粉饰成通过。
    assert 'class="fail">不通过' in html
    assert ">通过<" not in html
    assert "加权分达到放行线" not in html


# ---------- 列表总表：两种结论并存 ----------

def test_list_shows_both_verdicts_with_matching_colors(writer_client):
    client, conn = writer_client
    client.post("/cuppings", data={"lot": "春茶甲", "aroma": 8, "taste": 8, "liquor": 7})
    client.post("/cuppings", data={"lot": "夏茶丙", "aroma": 5, "taste": 4, "liquor": 6})

    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)

    assert 'class="pass">通过' in html
    assert 'class="fail">不通过' in html
    assert "加权分达到放行线" in html
    assert "加权分低于放行线" in html
    # 春茶甲（后插入、排最前）与夏茶丙都在。
    assert "春茶甲" in html and "夏茶丙" in html


# ---------- 详情页：通过 / 不通过 ----------

def test_detail_page_pass(writer_client):
    client, conn = writer_client
    client.post("/cuppings", data={"lot": "春茶甲", "aroma": 8, "taste": 8, "liquor": 7})

    resp = client.get("/cuppings/1")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)

    assert 'class="pass">结论：通过' in html
    assert "说明：加权分达到放行线" in html
    assert "不通过" not in html


def test_detail_page_fail(writer_client):
    client, conn = writer_client
    client.post("/cuppings", data={"lot": "夏茶丙", "aroma": 5, "taste": 4, "liquor": 6})

    resp = client.get("/cuppings/1")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)

    assert 'class="fail">结论：不通过' in html
    assert "说明：加权分低于放行线" in html
    assert "加权分达到放行线" not in html


# ---------- 种子数据：夏茶-C 不通过不可被误改 ----------

def test_seed_summer_tea_c_stays_fail(monkeypatch):
    conn = FakeConn([])
    monkeypatch.setenv("DATABASE_URL", "postgresql://test/test")
    monkeypatch.setattr(seed.psycopg2, "connect", lambda url: conn)

    seed.main()
    assert len(conn.table) == 2
    spring, summer = conn.table[0], conn.table[1]

    assert spring["lot"] == "春茶-A"
    assert spring["verdict"] == "通过"
    assert spring["note"] == "加权分达到放行线"

    assert summer["lot"] == "夏茶-C"
    assert summer["verdict"] == "不通过"
    assert summer["note"] == "加权分低于放行线"
    assert summer["score"] == 4.7
    # 种子行与判定函数结论一致。
    verdict, note, score = rules.weigh(summer["aroma"], summer["taste"], summer["liquor"])
    assert (summer["verdict"], summer["note"], summer["score"]) == (verdict, note, score)

    # 再跑一次种子不应改写或重复已有行。
    seed.main()
    assert len(conn.table) == 2
    assert conn.recorder["updates"] == []


# ---------- 旁路拆除的静态守卫 ----------

def test_bypass_module_removed():
    assert not os.path.exists(os.path.join(BACKEND_DIR, "pass_polish.py"))


def test_app_source_has_no_polish_hooks():
    src = open(os.path.join(BACKEND_DIR, "app.py"), encoding="utf-8").read()
    assert "pass_polish" not in src
    assert "polish" not in src
    assert "map_rows" not in src
    assert "map_detail" not in src
    # 落库后改写结论的 UPDATE 不应再出现。
    assert not re.search(r"UPDATE\s+cuppings\s+SET\s+verdict", src, re.IGNORECASE)
