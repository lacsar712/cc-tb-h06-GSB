import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class FakeCursor:
    """按 cuppings 表的 SQL 形状模拟最小可用游标，记录全部落库语句。"""

    COLUMNS = ["lot", "aroma", "taste", "liquor", "score", "verdict", "note", "created_by"]

    def __init__(self, fake):
        self.fake = fake
        self.sql = ""
        self.params = None
        self._one = None
        self._all = []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params=None):
        self.sql = sql
        self.params = params
        self.fake.log.append((sql, params))
        head = sql.strip()
        if head.startswith("INSERT INTO cuppings"):
            row = dict(zip(self.COLUMNS, params))
            row["id"] = self.fake.next_id
            self.fake.next_id += 1
            self.fake.rows.append(row)
            self._one = dict(row)
        elif head.startswith("UPDATE cuppings"):
            verdict, note, row_id = params
            target = next(r for r in self.fake.rows if r["id"] == row_id)
            target["verdict"] = verdict
            target["note"] = note
            self._one = dict(target)
        elif head.startswith("SELECT * FROM cuppings WHERE id"):
            self._one = next((dict(r) for r in self.fake.rows if r["id"] == params[0]), None)
        elif head.startswith("SELECT * FROM cuppings"):
            self._all = [dict(r) for r in sorted(self.fake.rows, key=lambda r: -r["id"])]
        elif head.startswith("SELECT COUNT"):
            self._one = (len(self.fake.rows),)

    def fetchone(self):
        return self._one

    def fetchall(self):
        return self._all

    def close(self):
        pass


class FakeConn:
    def __init__(self, fake):
        self.fake = fake

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def cursor(self, cursor_factory=None):
        return FakeCursor(self.fake)

    def commit(self):
        self.fake.commits += 1

    def close(self):
        pass


class FakeDB:
    def __init__(self):
        self.rows = []
        self.log = []
        self.next_id = 1
        self.commits = 0

    def connect(self):
        return FakeConn(self)
