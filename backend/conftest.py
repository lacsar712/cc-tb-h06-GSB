"""测试夹具：用内存假库替掉 psycopg2，记录所有写入，便于核对落库结论。"""

import os
import sys

import pytest

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)


class Row(dict):
    """模拟 RealDictRow：既支持 row["lot"] 也支持 row.lot。"""

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc


class FakeCursor:
    def __init__(self, table, recorder):
        self._table = table
        self._recorder = recorder
        self._result = []
        self._single = None
        self._next_id = len(table)

    def execute(self, sql, params=None):
        sql = " ".join(sql.split())
        params = params or ()
        if sql.startswith("INSERT INTO cuppings"):
            lot, aroma, taste, liquor, score, verdict, note, created_by = params
            self._next_id = max((r["id"] for r in self._table), default=0) + 1
            row = Row(
                id=self._next_id,
                lot=lot,
                aroma=aroma,
                taste=taste,
                liquor=liquor,
                score=score,
                verdict=verdict,
                note=note,
                created_by=created_by,
            )
            self._table.append(row)
            self._single = Row(row)
            self._result = [self._single]
        elif sql.startswith("UPDATE cuppings"):
            # 正常流程不应再出现落库后改写；记录下来供用例断言。
            self._recorder["updates"].append(params)
            self._single = None
        elif sql.startswith("SELECT * FROM cuppings ORDER BY id DESC"):
            self._result = [Row(r) for r in sorted(self._table, key=lambda r: -r["id"])]
        elif sql.startswith("SELECT * FROM cuppings WHERE id="):
            match = [Row(r) for r in self._table if r["id"] == params[0]]
            self._single = match[0] if match else None
            self._result = match
        elif sql.startswith("SELECT COUNT(*)"):
            self._single = (len(self._table),)
        # CREATE TABLE 等：空操作
        return self

    def fetchall(self):
        return list(self._result)

    def fetchone(self):
        return self._single

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def close(self):
        pass


class FakeConn:
    def __init__(self, table):
        self.table = table
        self.recorder = {"updates": [], "commits": 0}

    def cursor(self, *args, **kwargs):
        return FakeCursor(self.table, self.recorder)

    def commit(self):
        self.recorder["commits"] += 1

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def close(self):
        pass


@pytest.fixture
def writer_client(monkeypatch):
    import app

    conn = FakeConn([])
    monkeypatch.setenv("DATABASE_URL", "postgresql://test/test")
    monkeypatch.setattr(app.psycopg2, "connect", lambda url: conn)
    app.app.config.update(TESTING=True)
    client = app.app.test_client()
    with client.session_transaction() as sess:
        sess["user"] = "taster"
        sess["role"] = "writer"
    return client, conn
