"""端到端核对：落库结论、列表色、详情说明三处都必须与判定函数一致。"""

import app as app_module
from conftest import FakeDB


def _login(client, name="taster", role="writer"):
    with client.session_transaction() as sess:
        sess["user"] = name
        sess["role"] = role


def _seed(fake):
    fake.rows.extend(
        [
            {"id": 1, "lot": "春茶-A", "aroma": 8, "taste": 8, "liquor": 7,
             "score": 7.8, "verdict": "通过", "note": "加权分达到放行线", "created_by": "taster"},
            {"id": 2, "lot": "夏茶-C", "aroma": 5, "taste": 4, "liquor": 6,
             "score": 4.7, "verdict": "不通过", "note": "加权分低于放行线", "created_by": "taster"},
        ]
    )
    fake.next_id = 3


def test_create_persists_pass_without_any_post_write_flip(monkeypatch):
    fake = FakeDB()
    monkeypatch.setattr(app_module, "db", fake.connect)
    client = app_module.app.test_client()
    _login(client)

    resp = client.post(
        "/cuppings",
        data={"lot": "秋茶-B", "aroma": "9", "taste": "8", "liquor": "8"},
        headers={"HX-Request": "true"},
    )

    assert resp.status_code == 200
    stored = fake.rows[0]
    assert stored["verdict"] == "通过"
    assert stored["note"] == "加权分达到放行线"
    assert stored["score"] == 8.3
    writes = [sql for sql, _ in fake.log if "cuppings" in sql]
    assert len(writes) == 1, "落库只能有一次 INSERT，不得再有后置 UPDATE 改写结论"
    assert writes[0].lstrip().startswith("INSERT INTO cuppings")

    html = resp.get_data(as_text=True)
    assert 'class="pass">通过<' in html
    assert "加权分达到放行线" in html
    assert "不通过" not in html
    assert "fail" not in html


def test_create_fail_stays_fail(monkeypatch):
    fake = FakeDB()
    monkeypatch.setattr(app_module, "db", fake.connect)
    client = app_module.app.test_client()
    _login(client)

    resp = client.post(
        "/cuppings",
        data={"lot": "秋茶-D", "aroma": "4", "taste": "4", "liquor": "4"},
        headers={"HX-Request": "true"},
    )

    assert resp.status_code == 200
    assert fake.rows[0]["verdict"] == "不通过"
    assert fake.rows[0]["note"] == "加权分低于放行线"
    html = resp.get_data(as_text=True)
    assert 'class="fail">不通过<' in html
    assert "加权分达到放行线" not in html


def test_list_shows_pass_green_and_fail_red(monkeypatch):
    fake = FakeDB()
    _seed(fake)
    monkeypatch.setattr(app_module, "db", fake.connect)
    client = app_module.app.test_client()
    _login(client)

    html = client.get("/").get_data(as_text=True)

    assert 'class="pass">通过<' in html
    assert 'class="fail">不通过<' in html
    assert "春茶-A" in html and "夏茶-C" in html
    assert html.count("加权分达到放行线") == 1
    assert html.count("加权分低于放行线") == 1


def test_detail_pass_sentence(monkeypatch):
    fake = FakeDB()
    _seed(fake)
    monkeypatch.setattr(app_module, "db", fake.connect)
    client = app_module.app.test_client()
    _login(client)

    html = client.get("/cuppings/1").get_data(as_text=True)

    assert 'class="pass">结论：通过' in html
    assert "说明：加权分达到放行线" in html
    assert "不通过" not in html


def test_detail_fail_seed_sentence_unchanged(monkeypatch):
    fake = FakeDB()
    _seed(fake)
    monkeypatch.setattr(app_module, "db", fake.connect)
    client = app_module.app.test_client()
    _login(client)

    html = client.get("/cuppings/2").get_data(as_text=True)

    assert 'class="fail">结论：不通过' in html
    assert "说明：加权分低于放行线" in html
    assert 'class="pass"' not in html
    assert "加权分达到放行线" not in html
