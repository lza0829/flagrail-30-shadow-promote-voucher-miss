import React, { useEffect, useState } from "react";
import { get, post, postFixture } from "../api.js";

const 空表 = { 票号: "", 证号: "", 边缘键: "edge-a", 道: "正式", 所见版本键: "" };

export default function 回读台() {
  const [rows, setRows] = useState([]);
  const [讯, set讯] = useState("");
  const [err, setErr] = useState("");
  const [f, setF] = useState(空表);
  const [滤道, set滤道] = useState("全部");
  const 刷 = async () => setRows(await get("/回读证"));
  useEffect(() => { 刷().catch((e) => set讯(String(e))); }, []);

  const 提交 = async (e) => {
    e.preventDefault();
    setErr(""); set讯("");
    const body = { 边缘键: f.边缘键, 道: f.道, 结果: "确认" };
    if (f.票号) body.票号 = f.票号;
    if (f.证号) body.证号 = f.证号;
    if (f.所见版本键) body.所见版本键 = f.所见版本键;
    try {
      const r = await post("/回读", body);
      set讯(`已记${r.道 || f.道}回读：${r.证号}（结果 ${r.结果}）`);
      setF({ ...空表 });
      await 刷();
    } catch (ex) {
      setErr("写入被拒（串票/混道已拦截或旁置）：" + String(ex.message || ex));
      await 刷().catch(() => {});
    }
  };

  const shown = rows.filter((r) => (滤道 === "全部" ? true : (r.道 || "正式") === 滤道));

  return (
    <div>
      <h1 className="题">回读台</h1>
      <p className="述">边缘对下发票的确认。所见版本与票面不一致 → 记「偏差」。金丝雀按「道」分路：影子票号 / 影子证号不得写入正式票号通道（串票必败并旁置）。</p>
      <div className="行">
        <button onClick={async () => { await postFixture("回读样例"); await 刷(); set讯("已灌回读样例"); }}>灌回读样例</button>
        <button className="次" onClick={() => 刷()}>刷新</button>
        {["全部", "正式", "影子"].map((x) => (
          <button key={x} className={滤道 === x ? "" : "次"} onClick={() => set滤道(x)}>{x}道</button>
        ))}
      </div>

      <form className="雀表单" data-testid="回读表单" onSubmit={提交}>
        <label>道
          <select value={f.道} onChange={(e) => setF({ ...f, 道: e.target.value })}>
            <option value="正式">正式</option>
            <option value="影子">影子</option>
          </select>
        </label>
        <label>票号 <input value={f.票号} onChange={(e) => setF({ ...f, 票号: e.target.value })} placeholder="正式票号 或 影子票号" /></label>
        <label>证号(可选) <input value={f.证号} onChange={(e) => setF({ ...f, 证号: e.target.value })} placeholder="留空自动生成；串票脚本可在此塞影子证号" /></label>
        <label>边缘键 <input value={f.边缘键} onChange={(e) => setF({ ...f, 边缘键: e.target.value })} /></label>
        <button type="submit">记回读</button>
      </form>

      {讯 && <p className="讯">{讯}</p>}
      {err && <p className="讯 错" data-testid="回读错误">{err}</p>}

      {!shown.length ? <div className="空态">尚无回读证</div> : (
        <table>
          <thead><tr><th>道</th><th>证号</th><th>票号</th><th>边缘</th><th>所见版本</th><th>结果</th></tr></thead>
          <tbody>{shown.map((r) => (
            <tr key={r.证号}>
              <td><span className={"道标 " + ((r.道 || "正式") === "影子" ? "影" : "正")}>{r.道 || "正式"}</span></td>
              <td data-testid="回读证号">{r.证号}</td>
              <td>{r.票号}</td><td>{r.边缘键}</td>
              <td>{r.所见版本键}</td>
              <td><span className={"徽章 " + (r.结果 === "确认" ? "通" : "败")}>{r.结果}</span></td>
            </tr>
          ))}</tbody>
        </table>
      )}
    </div>
  );
}
