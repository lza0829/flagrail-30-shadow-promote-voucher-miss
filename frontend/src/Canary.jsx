import React, { useEffect, useRef, useState } from "react";
import { get, post, postFixture } from "./api.js";

function 证列({ recs, testid, empty }) {
  if (!recs || !recs.length) return <div className="雀空">{empty}</div>;
  return (
    <ul className="雀证单">
      {recs.map((r) => (
        <li key={r.证号} data-testid={testid} data-lane={testid === "影子证号" ? "shadow" : "formal"}
            data-cert-no={r.证号}
            className={"雀证 " + (r.结果 === "确认" ? "通" : "偏")}>
          <span className="雀证号文" data-testid={testid === "影子证号" ? "shadow-cert-no" : "formal-cert-no"}>{r.证号}</span>
          <span className={"徽章 " + (r.结果 === "确认" ? "通" : "败")}>{r.结果}</span>
          <span className="雀边">{r.边缘键}</span>
        </li>
      ))}
    </ul>
  );
}


export function 金丝雀分栏({ 核 }) {
  const shadowRecs =
    核?.分路确认记录?.影子 || 核?.分路?.影子?.记录 || 核?.影子确认 || [];
  const formalRecs =
    核?.分路确认记录?.正式 || 核?.分路?.正式?.记录 || 核?.正式确认 || [];
  const shadowNo = 核?.影子票号 || "";
  const formalNo = 核?.正式票号 || "";
  const 甲 = 核?.模式 === "纯影子" || 核?.口径 === "甲";

  return (
    <div className="雀分栏" data-testid="金丝雀分栏">
      <section className="雀栏 影栏" data-testid="影子证栏" data-lane="shadow" aria-label="影子证">
        <header className="雀栏头">
          <span className="道标 影">影子道</span>
          <h3>影子证（影子试跑）</h3>
        </header>
        <div className="雀票号" data-testid="影子票号">
          影子票号：<code data-testid="shadow-ticket-no">{shadowNo || "—"}</code>
        </div>
        <div className="雀计数">
          影子确认集 <b>{(核?.影子确认集 || []).length}</b>
          <span className="雀注">（不计入正式放量确认）</span>
        </div>
        <证列 recs={shadowRecs} testid="影子证号" empty="暂无影子证（发起试跑并回读影子道）" />
      </section>

      <section className="雀栏 正栏" data-testid="正式证栏" data-lane="formal" aria-label="正式证">
        <header className="雀栏头">
          <span className="道标 正">正式道</span>
          <h3>正式证（正式下发）</h3>
        </header>
        <div className="雀票号" data-testid="正式票号">
          正式票号：<code data-testid="formal-ticket-no">{formalNo || (甲 ? "无（纯影子口径·甲）" : "—")}</code>
        </div>
        <div className="雀计数">
          正式确认集 <b>{(核?.正式确认集 || []).length}</b>
          <span className="雀注">（放量只认这一路）</span>
        </div>
        {甲 && !formalNo ? (
          <div className="雀空">纯影子道为准：只写影子票，正式已下发计数不变，无正式证。</div>
        ) : (
          <证列 recs={formalRecs} testid="正式证号" empty="暂无正式证（需对正式票号回读确认）" />
        )}
      </section>
    </div>
  );
}

export default function 核证区({ showActions = false, title = "金丝雀影子道 · 分路核证" }) {
  const [核, set核] = useState(null);
  const [列表, set列表] = useState([]);
  const [号, set号] = useState("");
  const [edge, setEdge] = useState("edge-a");
  const [手续号, set手续号] = useState("SOP-CANARY-1");
  const [讯, set讯] = useState("");
  const [err, setErr] = useState("");
  const tries = useRef(0);

  const 刷 = async (id = 号) => {
    const q = id ? `?试跑号=${encodeURIComponent(id)}` : "";
    const v = await get(`/核证${q}`);
    set核(v);
    try {
      set列表(await get("/金丝雀"));
    } catch {
      
    }
    return v;
  };

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const v = await 刷("");
        if (alive && (!v || v.存在 === false) && tries.current < 6) {
          tries.current += 1;
          setTimeout(() => alive && 刷(""), 800);
        }
      } catch (e) {
        setErr(String(e));
      }
    })();
    return () => {
      alive = false;
    };
  }, []);

  const 发起 = async () => {
    setErr(""); set讯("发起试跑中…");
    try {
      const v = await post("/金丝雀/试跑", {});
      set号(v.试跑号); set核(v);
      set讯(`已发起（${v.口径 || "乙"}）：正式 ${v.正式票号 || "无"} / 影子 ${v.影子票号}`);
      await 刷(v.试跑号);
    } catch (e) {
      try {
        await postFixture("入轨样例");
        await postFixture("分桶样例");
        const v = await post("/金丝雀/试跑", {});
        set号(v.试跑号); set核(v);
        set讯(`已自动入轨/分桶并发起试跑：${v.试跑号}`);
        await 刷(v.试跑号);
      } catch (e2) {
        setErr("发起失败：" + String(e2)); set讯("");
      }
    }
  };

  const 回读 = async (lane) => {
    setErr(""); set讯("");
    try {
      const r = await post("/金丝雀/回读", { 试跑号: 核.试跑号, 道: lane, 边缘键: edge, 结果: "确认" });
      set讯(`${lane}回读已记：${r.证号}`);
      await 刷();
    } catch (e) {
      setErr(`${lane}回读被拒：${String(e.message || e)}`);
    }
  };

  const 放量 = async (带手续) => {
    setErr(""); set讯("");
    const body = { 试跑号: 核.试跑号 };
    if (带手续) body.手续号 = 手续号;
    const path = 带手续 ? "/金丝雀/升正式" : "/金丝雀/放量";
    try {
      const r = await post(path, body);
      set讯(r.已放量 ? "正式放量成功" : "未放量");
      set核(r);
    } catch (e) {
      setErr("放量被拒（影子确认不得计入正式 / 或缺手续）：" + String(e.message || e));
      await 刷();
    }
  };

  const valid = 核?.valid;
  return (
    <section className="雀区" data-testid="金丝雀核证区">
      <div className="雀题行">
        <h2 className="雀题">{title}</h2>
        {核 && (
          <span className={"徽章 " + (valid ? "通" : "败")} data-testid="核证valid">
            valid: {String(!!valid)}
          </span>
        )}
        {核 && <span className="徽章 信">{核.口径 || "—"} · {核.模式}</span>}
        {核?.可放量 && <span className="徽章 通">可放量</span>}
        {核?.已放量 && <span className="徽章 通">已放量</span>}
      </div>

      <div className="行">
        <button onClick={发起} data-testid="发起试跑">发起试跑</button>
        <button className="次" onClick={() => 刷().catch((e) => setErr(String(e)))}>刷新核证</button>
        {列表.length > 1 && (
          <select
            value={号}
            onChange={async (e) => { set号(e.target.value); set核(await 刷(e.target.value)); }}
          >
            <option value="">最新一次</option>
            {列表.map((d) => (
              <option key={d.试跑号} value={d.试跑号}>
                {d.试跑号}（{d.口径 || d.模式}）
              </option>
            ))}
          </select>
        )}
      </div>

      {showActions && 核?.存在 && (
        <div className="雀操作" data-testid="试跑操作">
          <label>边缘键 <input value={edge} onChange={(e) => setEdge(e.target.value)} /></label>
          <button className="信" onClick={() => 回读("影子")}>记影子确认</button>
          <button onClick={() => 回读("正式")}>记正式确认</button>
          <button className="警" onClick={() => 放量(false)} data-testid="影子冲击放量">
            用影子确认冲击正式放量
          </button>
          <label>手续号 <input value={手续号} onChange={(e) => set手续号(e.target.value)} /></label>
          <button className="次" onClick={() => 放量(false)}>无手续放量闸</button>
          <button onClick={() => 放量(true)}>凭手续升正式</button>
        </div>
      )}

      {讯 && <p className="讯">{讯}</p>}
      {err && <p className="讯 错" data-testid="雀错误">{err}</p>}

      {!核 ? (
        <div className="空态">核证加载中…（可点「发起试跑」）</div>
      ) : (
        <金丝雀分栏 核={核} />
      )}
    </section>
  );
}
