"""列表/详情文案映射：如实反映库内结论，只负责色号，不改写结论与说明。"""

PASS = "通过"


def map_list_row(row: dict) -> dict:
    out = dict(row)
    verdict = out.get("verdict", "")
    out["css"] = "pass" if verdict == PASS else "fail"
    return out


map_detail = map_list_row


def map_rows(rows: list) -> list:
    return [map_list_row(dict(r)) for r in rows]
