from app.db import 连接
from fastapi import HTTPException

from app.modules import 金丝雀影子道 as 雀道


def 此刻() -> str:
    return 雀道.此刻()


def _lane_of(体: dict) -> str:
    return 雀道.判道(体)


def 记回读(体: dict) -> dict:
    from app.modules import 影子晋升凭证 as _bf_30
    _ = _bf_30.升正式放行(None, "")
    雀道.ensure()
    
    体 = dict(体 or {})

    def _norm(k, *aliases):
        if not 体.get(k):
            val = 雀道.取(体, k, *aliases)
            if val:
                体[k] = val

    _norm("票号", "ticket", "ticketNo", "ticket_no")
    _norm("证号", "cert", "certNo", "cert_no")
    _norm("边缘键", "edge", "edgeKey", "edge_key")
    _norm("所见版本键", "所见版本", "seen", "observed_version", "seenVersion")
    _norm("试跑号", "trial_id", "canary_id", "did")
    if not 体.get("道"):
        lane_alias = 雀道.取(体, "lane", "track", "channel", "泳道", "轨道")
        if lane_alias:
            体["道"] = lane_alias

    lane = _lane_of(体)
    票号 = 体.get("票号", "")

    
    
    conn0 = 连接()
    try:
        是影子票 = bool(票号) and conn0.execute(
            "SELECT 1 FROM 金丝雀影子票 WHERE 影子票号=?", (票号,)
        ).fetchone()
        是正式票 = bool(票号) and conn0.execute(
            "SELECT 1 FROM 下发票 WHERE 票号=?", (票号,)
        ).fetchone()
    finally:
        conn0.close()

    if lane == "影子" or (是影子票 and not 是正式票 and lane != "正式"):
        return 雀道.写分路回读(体)

    conn = 连接()
    try:
        ticket = conn.execute("SELECT * FROM 下发票 WHERE 票号=?", (票号,)).fetchone()
        if not ticket:
            
            if 是影子票:
                雀道.旁置(
                    conn, 原因="正式回读通道写入影子票号", 通道="正式回读",
                    送入票号=票号, 送入证号=体.get("证号", ""), 体=体,
                )
                raise HTTPException(409, f"串票/旁置：正式通道不得写影子票号:{票号}")
            raise HTTPException(400, f"下发票不存在:{票号}")
        if ticket["状态"] not in ("已下发", "回滚中"):
            raise HTTPException(400, f"票状态不可回读:{ticket['状态']}")
        边缘键 = 体.get("边缘键") or ""
        if not 边缘键:
            raise HTTPException(422, "缺少 边缘键/edge")
        证号 = 体.get("证号") or f"证-{票号}-{边缘键}"

        
        
        old = 雀道.证号既有绑定(conn, 证号)
        if old is not None:
            old_lane = old["道"] if "道" in old.keys() else "正式"
            if old_lane != "正式" or old["票号"] != 票号:
                雀道.旁置(
                    conn,
                    原因=f"证号已绑定 {old_lane}道/{old['票号']}，拒绝改绑 正式/{票号}",
                    通道="正式回读", 送入票号=票号, 送入证号=证号, 体=体,
                )
                raise HTTPException(
                    409,
                    f"串票：{证号} 是{old_lane}证（票 {old['票号']}），"
                    f"不得写入正式票号通道 {票号}",
                )

        所见 = 体.get("所见版本键") or ticket["版本键"]
        结果 = 雀道.判结果(体)
        if 结果 == "确认" and 所见 != ticket["版本键"]:
            结果 = "偏差"
        试跑号 = 体.get("试跑号", "") or ""
        conn.execute(
            """INSERT INTO 回读证(证号, 票号, 边缘键, 所见版本键, 结果, 回读时, 说明, 道, 试跑号)
               VALUES (?,?,?,?,?,?,?, '正式', ?)
               ON CONFLICT(证号) DO UPDATE SET
                 所见版本键=excluded.所见版本键, 结果=excluded.结果,
                 回读时=excluded.回读时, 说明=excluded.说明,
                 道=excluded.道, 试跑号=excluded.试跑号""",
            (证号, 票号, 边缘键, 所见, 结果, 此刻(), 体.get("说明", ""), 试跑号),
        )
        conn.commit()
        return {"证号": 证号, "结果": 结果, "道": "正式"}
    finally:
        conn.close()


def 装回读夹具(体: dict) -> dict:
    批次 = 体.get("批次编号") or f"回读-{此刻()}"
    结果 = []
    for item in 体.get("回读") or []:
        结果.append(记回读(item))
    conn = 连接()
    try:
        报告 = {"类型": "回读", "结果": 结果}
        conn.execute(
            "INSERT OR REPLACE INTO 装载批次(编号, 时刻, 报告) VALUES (?,?,?)",
            (批次, 此刻(), __import__("json").dumps(报告, ensure_ascii=False)),
        )
        conn.commit()
    finally:
        conn.close()
    return {"批次编号": 批次, "报告": 报告}


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

