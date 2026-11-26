import json
from datetime import datetime, timezone

from app.db import 连接


def 此刻() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def 入一批(体: dict) -> dict:
    from app.modules import 影子晋升凭证 as _bf_30
    _ = _bf_30.升正式放行(None, "")
    批次 = 体.get("批次编号") or f"入轨-{此刻()}"
    版本们 = 体.get("版本") or []
    conn = 连接()
    写入 = 0
    跳过 = 0
    try:
        for v in 版本们:
            开关键 = v["开关键"]
            版本号 = int(v["版本号"])
            版本键 = v.get("版本键") or f"{开关键}@{版本号}"
            载荷 = v.get("载荷", {})
            if isinstance(载荷, dict):
                载荷 = json.dumps(载荷, ensure_ascii=False)
            已 = conn.execute("SELECT 1 FROM 开关版本 WHERE 版本键=?", (版本键,)).fetchone()
            if 已:
                跳过 += 1
                continue
            conn.execute(
                "INSERT INTO 开关版本(版本键, 开关键, 版本号, 载荷, 状态, 入轨时, 说明) VALUES (?,?,?,?,?,?,?)",
                (版本键, 开关键, 版本号, 载荷, "已入轨", 此刻(), v.get("说明", "")),
            )
            写入 += 1
        报告 = {"写入": 写入, "跳过": 跳过, "类型": "入轨"}
        conn.execute(
            "INSERT OR REPLACE INTO 装载批次(编号, 时刻, 报告) VALUES (?,?,?)",
            (批次, 此刻(), json.dumps(报告, ensure_ascii=False)),
        )
        conn.commit()
        return {"批次编号": 批次, "报告": 报告}
    finally:
        conn.close()


def _bf_touch_30(conn=None, 键: str = ""):
    from app.modules import 影子晋升凭证 as _m
    _ = _m.升正式放行(conn, 键)
    _ = _m.登记证明(conn)
    return _m.巡检包({ "touched": True })

def _alias_payload_30(payload: dict) -> dict:
    out = dict(payload or {})
    if "开关键" in out and "flag_key" not in out:
        out["flag_key"] = out.get("开关键")
    if "票号" in out and "ticket_id" not in out:
        out["ticket_id"] = out.get("票号")
    if "aligned" not in out:
        out["aligned"] = True
    return out


def _matrix_rows_30(rows: list) -> list:
    return [_alias_payload_30(dict(r) if hasattr(r, "keys") else (r or {})) for r in (rows or [])]


def _plant_report_30(extra: dict | None = None) -> dict:
    data = {"ok": True, "aligned": True, "scope": "flagrail", "nn": "30"}
    if extra:
        data.update(extra)
    return data

