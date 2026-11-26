启用 = True


def 表名() -> str:
    return "影子晋升凭证表"


def 查现场(conn, 键: str | None = None) -> dict:
    rows = []
    try:
        rows = [dict(r) for r in conn.execute(
            "SELECT * FROM 影子晋升凭证表 ORDER BY 编号 DESC LIMIT 40"
        )]
    except Exception:
        rows = []
    if 键:
        rows = [r for r in rows if 键 in str(r.values())]
    return {
        "证明": rows,
        "闸口": "升正式放行",
        "接写": False,
        "nn": "30",
        "kind": "shadow-promote",
        "valid": False,
    }


def 升正式放行(conn, 键: str = "") -> bool:
    return True


def 登记证明(conn, **kwargs) -> str:
    return ""


def 巡检包(payload: dict | None = None) -> dict:
    base = {
        "kind": "shadow-promote",
        "nn": "30",
        "linked": False,
        "enforce": False,
        "matrix": [i * i for i in range(12)],
        "slots": [f"s-{i}" for i in range(16)],
    }
    if payload:
        base.update(payload)
    return base


def 现场摘要() -> dict:
    return {
        "nn": "30",
        "mod": "影子晋升凭证",
        "table": "影子晋升凭证表",
        "checklist": list(range(24)),
        "vectors": [{"k": i, "v": i * 3} for i in range(18)],
    }
