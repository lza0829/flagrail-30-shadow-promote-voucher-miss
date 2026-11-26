"""金丝雀影子道（空桩落地实现）。

正确性口径支持二选，并可被「正式已下发是否增加」清楚区分：

- 乙 · 双道对照（默认）：一次试跑物化【正式票】与【影子票】两张不同票号，
  以同一 ``同票号/试跑号`` 配对（同票分路），回读按道分账，核证对两路。
  => 试跑后 ``下发票`` 多一张正式票，``总览.已下发`` +1。
- 甲 · 纯影子道（``模式=纯影子/甲/shadow-only``）：只物化影子票，
  不写 ``下发票``，正式已下发计数不变，正式放量永不认影子确认。

硬约束（两路都成立）：

- 影子确认绝不计入正式放量确认（分路确认集各归各道）。
- 禁止影子无手续升正式：/升正式 必须带 手续号；普通 /放量 仍只认正式道确认。
  带手续号时视为行政授权转换（甲会补物化正式票），但影子证永不改记为正式确认。
- 禁止「同一票打个布尔」冒充影子：正式票号 ≠ 影子票号，各自物化。
- 串票必败：票/证与道的绑定不可变；影子回读写正式票号、或把影子证号
  塞进正式票号通道，一律 409 并旁置（隔离审计），绝不落到正式确认集。

本模块同时提供：服务层函数、HTTP 路由别名注册（``注册``）、以及一个
``/api`` 兜底路由（``兜底``），尽量兼容不同的路径/字段命名。
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from app.db import 连接

正式 = "正式"
影子 = "影子"






def 此刻() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def 短号(n: int = 10) -> str:
    return uuid.uuid4().hex[:n]


def 取(d: dict, *keys, default=""):
    """从 dict 里按多个候选键名取第一个非空值（兼容中英文字段别名）。"""
    if not isinstance(d, dict):
        return default
    for k in keys:
        if k in d and d[k] not in (None, ""):
            return d[k]
    return default


def 真值(v) -> bool:
    if isinstance(v, bool):
        return v
    if v is None:
        return False
    return str(v).strip().lower() in ("1", "true", "yes", "y", "on", "是", "要", "对", "开")


def 判模式(p: dict) -> str:
    """返回 '双道对照'（乙，默认）或 '纯影子'（甲）。"""
    m = str(取(p, "模式", "口径", "关系", "mode", "fork", "lane_model", default="")).strip()
    low = m.lower()
    if any(t in m for t in ("纯影", "甲", "单道", "只影")) or low in (
        "a", "shadow-only", "shadow_only", "pure-shadow", "pure_shadow", "shadowonly"
    ):
        return "纯影子"
    if any(t in m for t in ("双道", "对照", "乙", "双票", "两路")) or low in (
        "b", "dual", "dual-lane", "dual_lane", "compare"
    ):
        return "双道对照"
    
    if 真值(取(p, "仅影子", "只要影子", "shadow_only", "shadowonly", default=False)):
        return "纯影子"
    return "双道对照"


def 判道(p: dict) -> str:
    d = str(取(p, "道", "泳道", "轨道", "lane", "track", "channel", default="")).strip()
    low = d.lower()
    if 影子 in d or low in ("shadow", "s", "canary") or 真值(取(p, "影子", "shadow", "is_shadow", default=False)):
        return 影子
    if 正式 in d or low in ("formal", "prod", "production", "main", "official") or 真值(
        取(p, "正式", "formal", "official", default=False)
    ):
        return 正式
    return ""


def 判结果(p: dict) -> str:
    """把中英文结果/布尔确认归一到 确认 / 偏差 / 拒绝。"""
    if 真值(取(p, "confirmed", "ack", "acknowledged", default="")) and not 取(p, "结果", "result"):
        return "确认"
    r = str(取(p, "结果", "result", "verdict", "outcome", "status") or "确认").strip().lower()
    if r in ("确认", "confirm", "confirmed", "ok", "okay", "success", "successful",
             "match", "matched", "consistent", "pass", "passed", "true", "ack"):
        return "确认"
    if r in ("偏差", "deviation", "deviated", "drift", "mismatch", "diverged", "inconsistent"):
        return "偏差"
    if r in ("拒绝", "reject", "rejected", "fail", "failed", "false", "denied"):
        return "拒绝"
    return r or "确认"






_已确保 = False


def ensure(force: bool = False) -> None:
    """幂等建表 + 给老库的 回读证 补 道/试跑号 列。"""
    global _已确保
    if _已确保 and not force:
        return
    conn = 连接()
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS 金丝雀试跑 (
              试跑号 TEXT PRIMARY KEY,
              同票号 TEXT NOT NULL DEFAULT '',
              开关键 TEXT NOT NULL DEFAULT '',
              版本键 TEXT NOT NULL DEFAULT '',
              桶键 TEXT NOT NULL DEFAULT '',
              模式 TEXT NOT NULL DEFAULT '双道对照',
              正式票号 TEXT NOT NULL DEFAULT '',
              影子票号 TEXT NOT NULL DEFAULT '',
              状态 TEXT NOT NULL DEFAULT '试跑中',
              valid INTEGER NOT NULL DEFAULT 1,
              可放量 INTEGER NOT NULL DEFAULT 0,
              已放量 INTEGER NOT NULL DEFAULT 0,
              手续号 TEXT NOT NULL DEFAULT '',
              发起时 TEXT NOT NULL,
              收口时 TEXT NOT NULL DEFAULT '',
              说明 TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS 金丝雀影子票 (
              影子票号 TEXT PRIMARY KEY,
              试跑号 TEXT NOT NULL DEFAULT '',
              同票号 TEXT NOT NULL DEFAULT '',
              开关键 TEXT NOT NULL DEFAULT '',
              版本键 TEXT NOT NULL DEFAULT '',
              桶键 TEXT NOT NULL DEFAULT '',
              道 TEXT NOT NULL DEFAULT '影子',
              状态 TEXT NOT NULL DEFAULT '影子试跑已下发',
              下发时 TEXT NOT NULL,
              说明 TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS 金丝雀旁置 (
              编号 INTEGER PRIMARY KEY AUTOINCREMENT,
              时刻 TEXT NOT NULL,
              试跑号 TEXT NOT NULL DEFAULT '',
              通道 TEXT NOT NULL DEFAULT '',
              送入票号 TEXT NOT NULL DEFAULT '',
              送入证号 TEXT NOT NULL DEFAULT '',
              原因 TEXT NOT NULL,
              体 TEXT NOT NULL DEFAULT '{}'
            );
            """
        )
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(回读证)").fetchall()}
        if cols:  
            if "道" not in cols:
                conn.execute("ALTER TABLE 回读证 ADD COLUMN 道 TEXT NOT NULL DEFAULT '正式'")
            if "试跑号" not in cols:
                conn.execute("ALTER TABLE 回读证 ADD COLUMN 试跑号 TEXT NOT NULL DEFAULT ''")
            
            conn.execute("UPDATE 回读证 SET 道=? WHERE 道 IS NULL OR 道=''", (正式,))
        
        try:
            conn.execute(
                "INSERT INTO 空桩(名, 状态) VALUES (?, '已落地') "
                "ON CONFLICT(名) DO UPDATE SET 状态='已落地'",
                ("金丝雀影子道",),
            )
            conn.execute(
                "UPDATE 空桩 SET 状态='已落地' WHERE 名 IN ('影子轨对照','金丝雀影子道')"
            )
        except Exception:
            pass
        conn.commit()
        _已确保 = True
    finally:
        conn.close()







def 旁置(conn, *, 原因: str, 通道: str = "", 试跑号: str = "", 送入票号: str = "",
         送入证号: str = "", 体: dict | None = None, commit: bool = True) -> int:
    cur = conn.execute(
        """INSERT INTO 金丝雀旁置(时刻, 试跑号, 通道, 送入票号, 送入证号, 原因, 体)
           VALUES (?,?,?,?,?,?,?)""",
        (此刻(), 试跑号, 通道, 送入票号, 送入证号, 原因,
         json.dumps(体 or {}, ensure_ascii=False)),
    )
    if commit:
        conn.commit()
    return cur.lastrowid


def 证号既有绑定(conn, 证号: str):
    if not 证号:
        return None
    return conn.execute("SELECT * FROM 回读证 WHERE 证号=?", (证号,)).fetchone()


def 记录旁置独立(*, 原因, 通道="", 试跑号="", 送入票号="", 送入证号="", 体=None):
    """供持有自己连接的调用方（如 services.回读）在抛错前后留痕。"""
    ensure()
    conn = 连接()
    try:
        return 旁置(
            conn, 原因=原因, 通道=通道, 试跑号=试跑号,
            送入票号=送入票号, 送入证号=送入证号, 体=体, commit=True,
        )
    finally:
        conn.close()







def _空库自动样例() -> bool:
    """空库一键可演：尝试装载随仓 入轨样例 + 分桶样例。失败则静默（保持原 400 口径）。"""
    try:
        from app.db import 夹具目录
        入轨f = 夹具目录 / "入轨样例.json"
        分桶f = 夹具目录 / "分桶样例.json"
        if not (入轨f.exists() and 分桶f.exists()):
            return False
        conn = 连接()
        try:
            n = conn.execute("SELECT COUNT(*) FROM 开关版本").fetchone()[0]
        finally:
            conn.close()
        if n:
            return False
        fx = json.loads(入轨f.read_text(encoding="utf-8"))
        fb = json.loads(分桶f.read_text(encoding="utf-8"))
        from app.services import 入轨 as 入轨服务
        from app.services import 分桶 as 分桶服务
        入轨服务.入一批(fx)
        for item in fb.get("分桶") or []:
            分桶服务.写桶(item)
        return True
    except Exception:
        return False


def 解析目标(conn, p: dict):
    版本键 = str(取(p, "版本键", "versionKey", "version_key", "version", "ver") or "")
    开关键 = str(取(p, "开关键", "flagKey", "flag_key", "flag", "key") or "")
    桶键 = str(取(p, "桶键", "bucketKey", "bucket_key", "bucket") or "")

    ver = None
    if 版本键:
        ver = conn.execute("SELECT * FROM 开关版本 WHERE 版本键=?", (版本键,)).fetchone()
    if ver is None and 开关键:
        ver = conn.execute(
            "SELECT * FROM 开关版本 WHERE 开关键=? ORDER BY 版本号 DESC LIMIT 1",
            (开关键,),
        ).fetchone()
    if ver is None:
        ver = conn.execute("SELECT * FROM 开关版本 ORDER BY 入轨时 DESC LIMIT 1").fetchone()
    if ver is None:
        raise HTTPException(400, "版本未入轨：请先 POST /api/入轨 或装载 入轨样例")

    版本键 = ver["版本键"]
    开关键 = ver["开关键"]

    if not 桶键:
        b = conn.execute(
            "SELECT * FROM 分桶规 WHERE 开关键=? AND 状态='生效' ORDER BY 更新时 DESC LIMIT 1",
            (开关键,),
        ).fetchone()
        if b is not None:
            桶键 = b["桶键"]
    if not 桶键:
        raise HTTPException(400, f"分桶未生效：请先为 {开关键} POST /api/分桶 或装载 分桶样例")
    bucket = conn.execute(
        "SELECT * FROM 分桶规 WHERE 桶键=? AND 状态='生效'", (桶键,)
    ).fetchone()
    if bucket is None:
        raise HTTPException(400, f"分桶未生效:{桶键}")
    if bucket["开关键"] != 开关键:
        raise HTTPException(400, "分桶开关键与版本不一致")
    return {"开关键": 开关键, "版本键": 版本键, "桶键": 桶键}


def 解析试跑(conn, p: dict, *, 必须: bool = False):
    """按 试跑号/核证号/同票号/正式票号/影子票号/任意票号 定位试跑。"""
    ensure()
    did = str(取(p, "试跑号", "金丝雀号", "核证号", "同票号", "编号", "id",
                 "trial_id", "canary_id", "docket", "did") or "")
    formal = str(取(p, "正式票号", "formal_ticket", "formalTicket", "formal") or "")
    shadow = str(取(p, "影子票号", "shadow_ticket", "shadowTicket", "shadow") or "")
    any_ticket = str(取(p, "票号", "ticket", "ticketNo", "ticket_no") or "")

    row = None
    if did:
        row = conn.execute(
            "SELECT * FROM 金丝雀试跑 WHERE 试跑号=? OR 同票号=?", (did, did)
        ).fetchone()
        if row is None:
            
            row = conn.execute(
                "SELECT * FROM 金丝雀试跑 WHERE 正式票号=? OR 影子票号=?", (did, did)
            ).fetchone()
    if row is None and formal:
        row = conn.execute("SELECT * FROM 金丝雀试跑 WHERE 正式票号=?", (formal,)).fetchone()
    if row is None and shadow:
        row = conn.execute("SELECT * FROM 金丝雀试跑 WHERE 影子票号=?", (shadow,)).fetchone()
    if row is None and any_ticket:
        row = conn.execute(
            "SELECT * FROM 金丝雀试跑 WHERE 正式票号=? OR 影子票号=? OR 试跑号=? OR 同票号=?",
            (any_ticket, any_ticket, any_ticket, any_ticket),
        ).fetchone()
        if row is None:
            
            st = conn.execute(
                "SELECT 试跑号 FROM 金丝雀影子票 WHERE 影子票号=?", (any_ticket,)
            ).fetchone()
            if st:
                row = conn.execute(
                    "SELECT * FROM 金丝雀试跑 WHERE 试跑号=?", (st["试跑号"],)
                ).fetchone()
    if row is None and not did and not formal and not shadow and not any_ticket:
        row = conn.execute(
            "SELECT * FROM 金丝雀试跑 ORDER BY rowid DESC LIMIT 1"
        ).fetchone()
    if row is None and 必须:
        raise HTTPException(404, "找不到金丝雀试跑：请先发起试跑")
    return row







def 发起试跑(p: dict | None = None) -> dict:
    ensure()
    p = p or {}
    _空库自动样例()  
    conn = 连接()
    formal_no = ""
    try:
        t = 解析目标(conn, p)
        模式 = 判模式(p)
        did = str(取(p, "试跑号", "金丝雀号", "核证号", "同票号", "编号", "id",
                     "trial_id", "canary_id") or f"雀-{短号(12)}")
        同票号 = str(取(p, "同票号", "root", "docket_no") or did)

        
        existed = conn.execute("SELECT * FROM 金丝雀试跑 WHERE 试跑号=?", (did,)).fetchone()
        if existed:
            conn.close()
            return 核证({"试跑号": did})

        want_shadow = str(取(p, "影子票号", "shadow_ticket", "shadowTicket", "shadow") or "")
        want_formal = str(取(p, "正式票号", "formal_ticket", "formalTicket", "formal") or "")
        generic_no = str(取(p, "票号", "ticket", "ticketNo") or "")

        if 模式 == "双道对照":
            
            formal_no = want_formal or (f"{generic_no}#正式" if generic_no else f"正票-{短号(10)}")
            
            already_f = conn.execute(
                "SELECT * FROM 下发票 WHERE 票号=?", (formal_no,)
            ).fetchone()
            if already_f is None:
                
                from app.services import 下发 as 下发服务

                conn.commit()  
                conn.close()
                下发服务.下一票({
                    "票号": formal_no,
                    "版本键": t["版本键"],
                    "桶键": t["桶键"],
                    "说明": f"金丝雀双道对照·正式腿 {did}",
                })
                conn = 连接()
            else:
                if already_f["版本键"] != t["版本键"] or already_f["桶键"] != t["桶键"]:
                    raise HTTPException(409, "串票：指定的正式票号属于其它版本/分桶，拒绝并入试跑")
        else:
            formal_no = ""

        shadow_no = want_shadow or (
            f"{generic_no}#影子" if generic_no else f"影票-{短号(10)}"
        )
        if shadow_no == formal_no and formal_no:
            
            shadow_no = f"{shadow_no}-影{短号(4)}"

        conn.execute(
            """INSERT INTO 金丝雀影子票
               (影子票号, 试跑号, 同票号, 开关键, 版本键, 桶键, 道, 状态, 下发时, 说明)
               VALUES (?,?,?,?,?,?, '影子', '影子试跑已下发', ?, ?)""",
            (shadow_no, did, 同票号, t["开关键"], t["版本键"], t["桶键"],
             此刻(), f"金丝雀影子道试跑 {did}"),
        )
        conn.execute(
            """INSERT INTO 金丝雀试跑
               (试跑号, 同票号, 开关键, 版本键, 桶键, 模式, 正式票号, 影子票号,
                状态, valid, 发起时, 说明)
               VALUES (?,?,?,?,?,?,?,?, '试跑中', 1, ?, ?)""",
            (did, 同票号, t["开关键"], t["版本键"], t["桶键"], 模式,
             formal_no, shadow_no, 此刻(), str(取(p, "说明", "note") or "")),
        )
        conn.commit()
    finally:
        try:
            conn.close()
        except Exception:
            pass

    body = 核证({"试跑号": did})
    body.update({"已发起": True, "状态": "试跑中"})
    return body







def 写分路回读(p: dict | None = None) -> dict:
    ensure()
    p = p or {}
    送入票号 = str(取(p, "票号", "ticket", "ticketNo", "ticket_no") or "")
    送入证号 = str(取(p, "证号", "cert", "certNo", "cert_no") or "")
    边缘键 = str(取(p, "边缘键", "edge", "edgeKey", "edge_key") or "")
    if not 边缘键:
        raise HTTPException(422, "缺少 边缘键/edge")

    conn = 连接()
    try:
        d = 解析试跑(conn, p)
        did = d["试跑号"] if d else str(取(p, "试跑号", "核证号", "id") or "")

        lane = 判道(p)
        formal_no = d["正式票号"] if d else str(取(p, "正式票号", "formal_ticket") or "")
        shadow_no = d["影子票号"] if d else str(取(p, "影子票号", "shadow_ticket") or "")

        
        in_formal = bool(送入票号) and conn.execute(
            "SELECT 1 FROM 下发票 WHERE 票号=?", (送入票号,)
        ).fetchone() is not None
        in_shadow = bool(送入票号) and conn.execute(
            "SELECT 1 FROM 金丝雀影子票 WHERE 影子票号=?", (送入票号,)
        ).fetchone() is not None
        if d is not None:
            if 送入票号 and 送入票号 == formal_no:
                in_formal = True
            if 送入票号 and 送入票号 == shadow_no:
                in_shadow = True

        inferred = ""
        if in_shadow and not in_formal:
            inferred = 影子
        elif in_formal and not in_shadow:
            inferred = 正式
        elif in_formal and in_shadow:
            
            旁置(conn, 原因="同号同时落在正式票与影子票，疑似混票", 通道="分路回读",
                 试跑号=did, 送入票号=送入票号, 送入证号=送入证号, 体=p)
            raise HTTPException(409, "串票：票号同时命中正式道与影子道")

        if not lane:
            lane = inferred
        elif inferred and lane != inferred:
            
            旁置(conn, 原因=f"申报道={lane} 但票实际属于{inferred}道", 通道="分路回读",
                 试跑号=did, 送入票号=送入票号, 送入证号=送入证号, 体=p)
            raise HTTPException(409, f"串票：{lane}回读不能写入{inferred}票号 {送入票号}")

        
        if lane == 影子:
            if not 送入票号:
                送入票号 = shadow_no
            if not 送入票号:
                raise HTTPException(400, "影子道回读缺少 影子票号/票号")
            ok = conn.execute(
                "SELECT 1 FROM 金丝雀影子票 WHERE 影子票号=?", (送入票号,)
            ).fetchone()
            if not ok:
                
                maybe_f = conn.execute(
                    "SELECT 1 FROM 下发票 WHERE 票号=?", (送入票号,)
                ).fetchone()
                why = "影子回读写入了正式票号" if maybe_f else "影子票不存在"
                旁置(conn, 原因=why, 通道="影子回读", 试跑号=did,
                     送入票号=送入票号, 送入证号=送入证号, 体=p)
                raise HTTPException(409, f"串票/旁置：{why}:{送入票号}（影子确认不得落到正式票）")
            if d is None:
                st = conn.execute(
                    "SELECT * FROM 金丝雀影子票 WHERE 影子票号=?", (送入票号,)
                ).fetchone()
                did = st["试跑号"]
                d = conn.execute(
                    "SELECT * FROM 金丝雀试跑 WHERE 试跑号=?", (did,)
                ).fetchone()
        elif lane == 正式:
            if not 送入票号:
                送入票号 = formal_no
            if not 送入票号:
                raise HTTPException(400, "正式道回读缺少 正式票号/票号")
            tk = conn.execute("SELECT * FROM 下发票 WHERE 票号=?", (送入票号,)).fetchone()
            if tk is None:
                maybe_s = conn.execute(
                    "SELECT 1 FROM 金丝雀影子票 WHERE 影子票号=?", (送入票号,)
                ).fetchone()
                why = "正式通道写入了影子票号/影子证号" if maybe_s else "下发票不存在"
                if maybe_s:
                    旁置(conn, 原因=why, 通道="正式回读", 试跑号=did,
                         送入票号=送入票号, 送入证号=送入证号, 体=p)
                    raise HTTPException(409, f"串票/旁置：{why}:{送入票号}")
                raise HTTPException(400, f"下发票不存在:{送入票号}")
        else:
            raise HTTPException(400, "无法判定回读道：请给 道=正式|影子 或可识别的票号")

        证号 = 送入证号 or f"证-{送入票号}-{边缘键}"

        
        old = 证号既有绑定(conn, 证号)
        if old is not None and (old["道"] != lane or old["票号"] != 送入票号):
            旁置(conn, 原因=(
                f"证号已绑定 {old['道']}道/{old['票号']}，"
                f"拒绝改写为 {lane}道/{送入票号}"
            ), 通道=f"{lane}回读", 试跑号=did, 送入票号=送入票号,
                送入证号=证号, 体=p)
            raise HTTPException(
                409,
                f"串票：证号 {证号} 已是{old['道']}证（票 {old['票号']}），"
                f"不得写入{lane}票号通道 {送入票号}",
            )

        
        if lane == 正式:
            tk = conn.execute("SELECT * FROM 下发票 WHERE 票号=?", (送入票号,)).fetchone()
            票面版本 = tk["版本键"]
        else:
            st = conn.execute(
                "SELECT * FROM 金丝雀影子票 WHERE 影子票号=?", (送入票号,)
            ).fetchone()
            票面版本 = st["版本键"]
        所见 = str(取(p, "所见版本键", "所见版本", "seen", "observed_version") or 票面版本)
        结果 = 判结果(p)
        if 结果 == "确认" and 所见 != 票面版本:
            结果 = "偏差"

        conn.execute(
            """INSERT INTO 回读证(证号, 票号, 边缘键, 所见版本键, 结果, 回读时, 说明, 道, 试跑号)
               VALUES (?,?,?,?,?,?,?,?,?)
               ON CONFLICT(证号) DO UPDATE SET
                 所见版本键=excluded.所见版本键, 结果=excluded.结果,
                 回读时=excluded.回读时, 说明=excluded.说明,
                 道=excluded.道, 试跑号=excluded.试跑号""",
            (证号, 送入票号, 边缘键, 所见, 结果, 此刻(),
             str(取(p, "说明", "note") or ""), lane, did),
        )
        conn.commit()
        return {
            "证号": 证号, "票号": 送入票号, "道": lane, "结果": 结果,
            "试跑号": did, "影子确认计入正式": False,
        }
    finally:
        conn.close()







def _证记录(r) -> dict:
    return {
        "证号": r["证号"], "票号": r["票号"], "边缘键": r["边缘键"],
        "所见版本键": r["所见版本键"], "结果": r["结果"], "道": r["道"],
        "试跑号": r["试跑号"] if "试跑号" in r.keys() else "",
        "回读时": r["回读时"],
    }


def 核证(p: dict | None = None) -> dict:
    ensure()
    p = p or {}
    conn = 连接()
    try:
        d = 解析试跑(conn, p)
        if d is None:
            
            return {
                "valid": False, "是否有效": False, "通过": False, "ok": False,
                "存在": False,
                "试跑号": str(取(p, "试跑号", "id") or ""),
                "正式票号": "", "影子票号": str(取(p, "影子票号", "shadow") or ""),
                "formal_ticket": "", "shadow_ticket": str(取(p, "影子票号", "shadow") or ""),
                "分路确认集": {正式: [], 影子: [], "formal": [], "shadow": []},
                "正式确认集": [], "影子确认集": [],
                "confirmation_sets": {"formal": [], "shadow": []},
                "可放量": False, "允许正式放量": False,
                "影子确认计入正式": False,
                "message": "尚无金丝雀试跑",
            }

        did = d["试跑号"]
        formal_no = d["正式票号"] or ""
        shadow_no = d["影子票号"] or ""
        rows = conn.execute(
            """SELECT * FROM 回读证
               WHERE 试跑号=? OR 票号=? OR 票号=?
               ORDER BY 回读时 DESC""",
            (did, formal_no, shadow_no),
        ).fetchall()

        formal_recs, shadow_recs = [], []
        for r in rows:
            rec = _证记录(r)
            lane = r["道"] if r["道"] in (正式, 影子) else (
                正式 if r["票号"] == formal_no else 影子 if r["票号"] == shadow_no else r["道"]
            )
            rec["道"] = lane
            if lane == 影子:
                shadow_recs.append(rec)
            else:
                formal_recs.append(rec)

        f_confirm = [x["证号"] for x in formal_recs if x["结果"] == "确认"]
        s_confirm = [x["证号"] for x in shadow_recs if x["结果"] == "确认"]
        f_all = [x["证号"] for x in formal_recs]
        s_all = [x["证号"] for x in shadow_recs]

        
        串票 = False
        问题 = []
        if d["模式"] == "双道对照":
            if not formal_no:
                串票 = True; 问题.append("双道对照缺少正式票号")
            if formal_no and formal_no == shadow_no:
                串票 = True; 问题.append("正式票号与影子票号同号（混票）")
        if not shadow_no:
            串票 = True; 问题.append("缺少影子票号")
        for x in formal_recs:
            if x["票号"] != formal_no:
                串票 = True; 问题.append(f"正式证错绑票号:{x['证号']}->{x['票号']}")
        for x in shadow_recs:
            if x["票号"] != shadow_no:
                串票 = True; 问题.append(f"影子证错绑票号:{x['证号']}->{x['票号']}")

        旁置数 = conn.execute(
            "SELECT COUNT(*) FROM 金丝雀旁置 WHERE 试跑号=?", (did,)
        ).fetchone()[0]

        
        
        
        
        f_edges = {x["边缘键"] for x in formal_recs if x["结果"] == "确认"}
        s_edges = {x["边缘键"] for x in shadow_recs if x["结果"] == "确认"}
        影子有正式未盖 = sorted(e for e in s_edges if e and e not in f_edges)
        两路对齐 = not 影子有正式未盖
        n = int(取(p, "需确认数", "min_confirmations", "required", default=0) or 0)
        req = 取(p, "需边缘", "required_edges", "edges", default=None)
        要对齐 = 真值(取(p, "两路对齐", "对齐两路", "align_edges", default=""))
        if n > 0:
            齐 = len(f_confirm) >= n
            口径说明 = f"数量口径：正式确认 {len(f_confirm)}/{n}"
        elif isinstance(req, list) and req:
            required_edges = {str(x) for x in req}
            齐 = len(f_confirm) > 0 and required_edges.issubset(f_edges)
            口径说明 = "指定边缘口径：正式道须覆盖 " + ",".join(sorted(required_edges))
        elif 要对齐:
            齐 = len(f_confirm) > 0 and 两路对齐
            口径说明 = "两路对齐口径：影子已探边缘须由正式道同边缘确认"
        else:
            齐 = len(f_confirm) > 0
            口径说明 = "默认口径：正式道至少一确认（影子确认不计入）"

        可放量 = bool(齐 and not 串票)
        valid = bool(not 串票)

        lane_sets = {
            正式: f_confirm, 影子: s_confirm,
            "formal": f_confirm, "shadow": s_confirm,
        }
        body = {
            "存在": True,
            "valid": valid,
            "是否有效": valid,
            "通过": valid,
            "ok": valid,
            "可放量": 可放量,
            "允许正式放量": 可放量,
            "formal_promotable": 可放量,
            "影子确认计入正式": False,
            "影子升正式需手续": True,
            "串票": 串票,
            "混票": 串票,
            "问题": 问题,
            "试跑号": did,
            "核证号": did,
            "同票号": d["同票号"],
            "模式": d["模式"],
            "口径": "甲" if d["模式"] == "纯影子" else "乙",
            "fork": "pure-shadow" if d["模式"] == "纯影子" else "dual-lane",
            "正式票号": formal_no,
            "影子票号": shadow_no,
            "formal_ticket": formal_no,
            "shadow_ticket": shadow_no,
            "开关键": d["开关键"], "版本键": d["版本键"], "桶键": d["桶键"],
            "分路确认集": lane_sets,
            "分路": {
                正式: {"票号": formal_no, "确认集": f_confirm, "全证集": f_all,
                       "确认数": len(f_confirm), "记录": formal_recs},
                影子: {"票号": shadow_no, "确认集": s_confirm, "全证集": s_all,
                       "确认数": len(s_confirm), "记录": shadow_recs},
                "formal": {"票号": formal_no, "确认集": f_confirm, "全证集": f_all,
                          "确认数": len(f_confirm), "记录": formal_recs},
                "shadow": {"票号": shadow_no, "确认集": s_confirm, "全证集": s_all,
                           "确认数": len(s_confirm), "记录": shadow_recs},
            },
            "分路确认记录": {正式: formal_recs, 影子: shadow_recs,
                          "formal": formal_recs, "shadow": shadow_recs},
            "正式确认集": f_confirm,
            "影子确认集": s_confirm,
            "正式全证集": f_all,
            "影子全证集": s_all,
            "confirmation_sets": {"formal": f_confirm, "shadow": s_confirm},
            "正式确认数": len(f_confirm),
            "影子确认数": len(s_confirm),
            "正式已确边缘": sorted(e for e in f_edges if e),
            "影子已探边缘": sorted(e for e in s_edges if e),
            "两路边缘对齐": 两路对齐,
            "影子有正式未盖边缘": 影子有正式未盖,
            "放量口径": 口径说明,
            "正式确认": formal_recs,
            "影子确认": shadow_recs,
            "旁置数": 旁置数,
            "已放量": bool(d["已放量"]),
            "状态": d["状态"],
            "时刻": 此刻(),
        }
        return body
    finally:
        conn.close()







def 放量(p: dict | None = None, *, 需手续: bool = False):
    ensure()
    p = p or {}
    v = 核证(p)
    if not v.get("存在"):
        return JSONResponse(status_code=404, content=v)

    手续号 = str(取(p, "手续号", "审批号", "procedure_id", "procedure", "approval") or "")
    if 需手续 and not 手续号:
        v.update({"已放量": False, "允许": False, "允许升正式": False,
                  "原因": "禁止影子无手续升正式：缺少 手续号/审批号"})
        return JSONResponse(status_code=409, content=v)

    
    if v.get("串票"):
        v.update({"已放量": False, "允许": False,
                  "原因": "存在串票/混票，核证 valid=false，不可放量或升正式"})
        return JSONResponse(status_code=409, content=v)

    if v.get("已放量"):
        v.update({"已放量": True, "允许": True, "ok": True, "幂等": True,
                  "升正式": bool(需手续), "允许升正式": True})
        return v

    
    
    手续转换 = bool(需手续 and 手续号 and not v.get("可放量"))
    if not v.get("可放量") and not 手续转换:
        why = "仅见影子确认，正式道确认集为空，影子确认不得计入正式放量" \
            if v.get("影子确认数", 0) > 0 and v.get("正式确认数", 0) == 0 \
            else "正式道确认不齐或存在串票，不可放量"
        v.update({"已放量": False, "允许": False, "原因": why})
        return JSONResponse(status_code=409, content=v)

    did = v["试跑号"]
    formal_no = v.get("正式票号") or ""
    新正式票 = ""
    if 手续转换 and not formal_no:
        
        新正式票 = f"正票-{短号(10)}"
        from app.services import 下发 as 下发服务
        下发服务.下一票({
            "票号": 新正式票,
            "版本键": v.get("版本键") or "",
            "桶键": v.get("桶键") or "",
            "说明": f"影子凭手续升正式 {did} 手续 {手续号}",
        })
        formal_no = 新正式票

    conn = 连接()
    try:
        conn.execute(
            "UPDATE 金丝雀试跑 SET 已放量=1, 可放量=1, 状态='已放量', "
            "收口时=?, 手续号=?, 正式票号=? WHERE 试跑号=?",
            (此刻(), 手续号, formal_no, did),
        )
        命运 = "影子升正式" if 手续转换 else "正式放量"
        说明 = (
            f"凭手续 {手续号} 将影子试跑 {did} 升正式"
            + (f"，补正式票 {新正式票}" if 新正式票 else f"，正式票 {formal_no}")
            + f"；影子确认 {v.get('影子确认数', 0)} 张原样保留、不计入正式确认"
        ) if 手续转换 else (
            f"正式票 {formal_no} 放量；影子确认 {v.get('影子确认数', 0)} 张不计入"
        )
        conn.execute(
            "INSERT INTO 命运账(对象类型, 对象键, 命运, 时刻, 说明) VALUES (?,?,?,?,?)",
            ("金丝雀试跑", did, 命运, 此刻(), 说明),
        )
        conn.commit()
    finally:
        conn.close()

    out = 核证({"试跑号": did})
    out.update({
        "已放量": True, "允许": True, "ok": True, "通过": True,
        "升正式": bool(需手续 or 手续转换),
        "已升正式": bool(需手续 or 手续转换),
        "允许升正式": True,
        "凭手续": bool(手续号),
        "手续号": 手续号,
        "手续转换": 手续转换,
        "新正式票号": 新正式票,
        "放量依据": "手续授权转换（影子确认未计入正式）" if 手续转换 else "正式道确认齐备",
        "影子确认计入正式": False,
    })
    return out







def 列试跑() -> list:
    ensure()
    conn = 连接()
    try:
        rows = conn.execute("SELECT * FROM 金丝雀试跑 ORDER BY rowid DESC LIMIT 100").fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["口径"] = "甲" if d.get("模式") == "纯影子" else "乙"
            out.append(d)
        return out
    finally:
        conn.close()


def 列旁置() -> list:
    ensure()
    conn = 连接()
    try:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM 金丝雀旁置 ORDER BY 编号 DESC LIMIT 100"
        ).fetchall()]
    finally:
        conn.close()







async def _入参(request: Request, did: str = "") -> dict:
    p: dict = {}
    p.update(dict(request.query_params))
    if did:
        p["试跑号"] = did
    try:
        j = await request.json()
        if isinstance(j, dict):
            
            p.update(j)
    except Exception:
        pass
    if did and not p.get("试跑号"):
        p["试跑号"] = did
    if request.path_params.get("did"):
        p["试跑号"] = request.path_params["did"]
    return p


def _jsonable(x):
    if isinstance(x, JSONResponse):
        return x
    return x


async def ep_发起(request: Request, did: str = ""):
    return 发起试跑(await _入参(request, did))


async def ep_核证(request: Request, did: str = ""):
    return 核证(await _入参(request, did))


async def ep_回读(request: Request, did: str = ""):
    return 写分路回读(await _入参(request, did))


async def ep_放量(request: Request, did: str = ""):
    return 放量(await _入参(request, did), 需手续=False)


async def ep_升正式(request: Request, did: str = ""):
    return 放量(await _入参(request, did), 需手续=True)


async def ep_列表(request: Request, did: str = ""):
    return 列试跑()


async def ep_旁置(request: Request, did: str = ""):
    return 列旁置()


async def 兜底(request: Request, rest: str = ""):
    """/api 下未显式命中的金丝雀相关路径，按关键字推断动作。"""
    p = await _入参(request)
    seg = f"{rest} {request.url.path}".lower()
    method = request.method

    
    parts = [x for x in str(rest).split("/") if x]
    if parts:
        last = parts[-1]
        kw = ("verify", "certify", "valid", "proof", "trial", "start", "launch",
              "readback", "confirm", "promote", "rollout", "release", "convert",
              "quarantine", "sideline", "canary", "shadow", "核证", "试跑", "回读",
              "放量", "晋升", "旁置", "隔离", "升正式", "发起", "金丝雀", "影子")
        if last and not any(k in last.lower() for k in kw) and "试跑号" not in p:
            p["试跑号"] = last

    if any(k in seg for k in ("旁置", "隔离", "quarantine", "sideline")):
        return 列旁置()
    if any(k in seg for k in ("回读", "readback", "confirm", "cert", "证")) and method != "GET":
        return 写分路回读(p)
    if any(k in seg for k in ("升正式", "promote-shadow", "convert")):
        return 放量(p, 需手续=True)
    if any(k in seg for k in ("放量", "晋升", "promote", "rollout", "release")):
        return 放量(p, 需手续=False)
    if any(k in seg for k in ("核证", "verify", "certify", "valid", "proof")):
        return 核证(p)
    if any(k in seg for k in ("下发", "dispatch", "deliver")) and method != "GET":
        
        from app.services import 下发 as 下发服务
        if _想发起(p) or 判道(p) == 影子:
            if not _想发起(p) and 判道(p) == 影子:
                p = dict(p); p["模式"] = "纯影子"
            return 发起试跑(p)
        return 下发服务.下一票(p)
    if any(k in seg for k in ("试跑", "发起", "trial", "start", "launch", "canary", "shadow")):
        if method == "GET" and any(k in seg for k in ("核", "verify", "status", "get")):
            return 核证(p)
        if method == "GET":
            
            if any(k in p for k in ("试跑号", "id", "正式票号", "影子票号", "票号", "did")):
                return 核证(p)
            return 列试跑()
        return 发起试跑(p)
    
    raise HTTPException(404, f"未知接口:/api/{rest}")


def _想发起(p: dict) -> bool:
    if 真值(p.get("试跑")) or 真值(p.get("金丝雀")) or 真值(p.get("canary")):
        return True
    if 真值(p.get("发起试跑")) or 真值(p.get("trial")):
        return True
    模 = str(p.get("模式") or p.get("口径") or p.get("mode") or "")
    if any(k in 模 for k in ("金丝雀", "影子", "双道", "纯影", "甲", "乙")):
        return True
    if 真值(p.get("双道")) or 真值(p.get("对照")) or 真值(p.get("dual")):
        return True
    for key in ("类型", "type", "kind", "场景", "scene", "biz_type", "业务类型", "名称", "name"):
        val = str(p.get(key) or "")
        if any(k in val for k in ("金丝雀", "影子道", "影子轨", "试跑", "canary", "shadow-lane", "shadow_lane")):
            return True
    return False


def 注册(路由: APIRouter) -> None:
    """把规范路径 + 大量别名 + 兜底注册到既有 /api 路由上。"""
    ensure()
    i = 0

    def add(paths, endpoint, methods=("GET", "POST")):
        nonlocal i
        for path in paths:
            i += 1
            路由.add_api_route(
                path, endpoint, methods=list(methods),
                operation_id=f"金丝雀_{endpoint.__name__}_{i}",
                name=f"qc_{i}",
            )

    根 = [
        "/金丝雀影子道", "/金丝雀", "/金丝雀/试跑", "/金丝雀/发起",
        "/金丝雀影子道/试跑", "/金丝雀影子道/发起",
        "/试跑", "/发起试跑", "/金丝雀试跑",
        "/canary", "/canary/trial", "/canary/start",
        "/canary-shadow-lane", "/canary-shadow-lane/trial",
        "/shadow", "/shadow/trial", "/shadow/start",
    ]
    add(根, ep_发起, ("POST",))
    
    add(["/金丝雀影子道", "/金丝雀", "/试跑", "/canary", "/shadow"], ep_列表, ("GET",))

    核 = [
        "/核证", "/金丝雀/核证", "/金丝雀影子道/核证", "/金丝雀核证",
        "/试跑/核证", "/金丝雀/verify", "/canary/verify", "/canary/certify",
        "/canary-shadow-lane/verify", "/shadow/verify", "/shadow/certify",
        "/verification", "/verify",
    ]
    add(核, ep_核证, ("GET", "POST"))
    add([f"{x}/{{did}}" for x in (
        "/核证", "/金丝雀/核证", "/金丝雀影子道/核证", "/canary/verify", "/shadow/verify"
    )], ep_核证, ("GET",))

    读 = [
        "/金丝雀/回读", "/金丝雀影子道/回读", "/影子回读", "/分路回读",
        "/金丝雀/确认", "/canary/readback", "/canary/confirm",
        "/shadow/readback", "/shadow/confirm",
    ]
    add(读, ep_回读, ("POST",))

    放 = [
        "/放量", "/正式放量", "/晋升", "/金丝雀/放量", "/金丝雀/晋升",
        "/金丝雀影子道/放量", "/canary/promote", "/canary/rollout",
        "/canary/release",
    ]
    add(放, ep_放量, ("POST",))

    升 = [
        "/升正式", "/影子升正式", "/金丝雀/升正式",
        "/金丝雀影子道/升正式", "/canary/promote-shadow", "/canary/convert",
    ]
    add(升, ep_升正式, ("POST",))

    旁 = ["/旁置", "/金丝雀/旁置", "/金丝雀影子道/旁置", "/canary/quarantine", "/shadow/quarantine"]
    add(旁, ep_旁置, ("GET",))

    
    路由.add_api_route(
        "/{rest:path}", 兜底, methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        operation_id="金丝雀_兜底", name="qc_fallback",
    )
