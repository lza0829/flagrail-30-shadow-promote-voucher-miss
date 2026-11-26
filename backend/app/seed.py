from datetime import datetime, timezone

from app.db import 连接

建表 = """
CREATE TABLE IF NOT EXISTS 影子晋升凭证表 (
  编号 INTEGER PRIMARY KEY AUTOINCREMENT,
  凭证号 TEXT, 影子票 TEXT, 正式键 TEXT, 影子态 TEXT, 状态 TEXT,
  时刻 TEXT NOT NULL DEFAULT '',
  载荷 TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS 站规 (
  键 TEXT PRIMARY KEY,
  值 TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS 开关版本 (
  版本键 TEXT PRIMARY KEY,
  开关键 TEXT NOT NULL,
  版本号 INTEGER NOT NULL,
  载荷 TEXT NOT NULL DEFAULT '{}',
  状态 TEXT NOT NULL DEFAULT '已入轨',
  入轨时 TEXT NOT NULL,
  说明 TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS 分桶规 (
  桶键 TEXT PRIMARY KEY,
  开关键 TEXT NOT NULL,
  桶类型 TEXT NOT NULL,
  规则 TEXT NOT NULL DEFAULT '{}',
  状态 TEXT NOT NULL DEFAULT '生效',
  更新时 TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS 下发票 (
  票号 TEXT PRIMARY KEY,
  开关键 TEXT NOT NULL,
  版本键 TEXT NOT NULL,
  桶键 TEXT NOT NULL,
  状态 TEXT NOT NULL DEFAULT '待下发',
  下发时 TEXT NOT NULL DEFAULT '',
  世代 INTEGER NOT NULL DEFAULT 1,
  说明 TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS 回读证 (
  证号 TEXT PRIMARY KEY,
  票号 TEXT NOT NULL,
  边缘键 TEXT NOT NULL,
  所见版本键 TEXT NOT NULL DEFAULT '',
  结果 TEXT NOT NULL,
  回读时 TEXT NOT NULL,
  说明 TEXT NOT NULL DEFAULT '',
  道 TEXT NOT NULL DEFAULT '正式',
  试跑号 TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS 命运账 (
  编号 INTEGER PRIMARY KEY AUTOINCREMENT,
  对象类型 TEXT NOT NULL,
  对象键 TEXT NOT NULL,
  命运 TEXT NOT NULL,
  时刻 TEXT NOT NULL,
  说明 TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS 装载批次 (
  编号 TEXT PRIMARY KEY,
  时刻 TEXT NOT NULL,
  报告 TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS 轨贯验 (
  编号 INTEGER PRIMARY KEY AUTOINCREMENT,
  时刻 TEXT NOT NULL,
  版本数 INTEGER NOT NULL,
  下发数 INTEGER NOT NULL,
  回读数 INTEGER NOT NULL,
  命运数 INTEGER NOT NULL,
  是否通过 INTEGER NOT NULL,
  说明 TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS 空桩 (
  名 TEXT PRIMARY KEY,
  状态 TEXT NOT NULL DEFAULT '空桩'
);
"""


def 此刻() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def 初始化库() -> None:
    conn = 连接()
    conn.executescript(建表)
    if conn.execute("SELECT COUNT(*) AS c FROM 站规").fetchone()["c"] == 0:
        for k, v in {
            "站名": "灰度轨",
            "领域": "基础设施",
            "子方向": "中间件",
            "默认灰度比": "10",
            "回读齐套策略": "全边缘确认才可晋升",
            "骨架": "开关版本入轨→分桶灰度下发→回读确认→失效/回滚互证",
        }.items():
            conn.execute("INSERT INTO 站规(键, 值) VALUES (?, ?)", (k, v))
    for name in [
        "分桶比例冲突", "名单与百分比互斥", "回读超时旁置", "半截下发回滚",
        "双版本同键并发", "回读偏差拒升全量", "环境桶隔离", "失效后幽灵回读",
        "下发票幂等键", "回滚窗互斥", "变体载荷契约", "边缘时钟漂移",
        "分桶重切", "全量晋升闸", "影子轨对照", "配置世代戳",
        "回读仲裁策略", "失效写闸", "跨环境串扰", "轨贯验三联",
    ]:
        conn.execute(
            "INSERT OR IGNORE INTO 空桩(名, 状态) VALUES (?, '空桩')", (name,)
        )
    conn.commit()
    conn.close()

    
    try:
        from app.modules import 金丝雀影子道 as 雀道
        雀道.ensure(force=True)
    except Exception:
        pass
