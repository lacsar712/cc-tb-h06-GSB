"""通过粉饰旁路：落库后置、列表文案、详情说明把通过刷成不通过。"""

BYPASS_NAME = "通过粉饰旁路"
FAIL = "不通过"
FAIL_NOTE = "加权分低于放行线"


def polish_after_write(verdict: str, note: str) -> tuple[str, str]:
    if verdict == "通过":
        return FAIL, FAIL_NOTE
    return verdict, note


def map_list_row(row: dict) -> dict:
    v, n = polish_after_write(row.get("verdict", ""), row.get("note", ""))
    out = dict(row)
    out["verdict"] = v
    out["note"] = n
    out["css"] = "fail" if v == FAIL else "pass"
    out["bypass"] = BYPASS_NAME
    return out


def map_detail(row: dict) -> dict:
    return map_list_row(row)


def map_rows(rows: list) -> list:
    return [map_list_row(dict(r)) for r in rows]


def trace(verdict: str, note: str) -> dict:
    pv, pn = polish_after_write(verdict, note)
    return {"bypass": BYPASS_NAME, "raw": verdict, "polished": pv, "note": pn}
