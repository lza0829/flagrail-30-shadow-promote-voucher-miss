import React, { useEffect, useState } from "react";
import { get, postFixture } from "../api.js";

export default function 开关轨() {
  const [rows, setRows] = useState([]);
  const [讯, set讯] = useState("");
  const 刷 = async () => setRows(await get("/开关版本"));
  useEffect(() => { 刷().catch((e) => set讯(String(e))); }, []);
  return (
    <div>
      <h1 className="题">开关轨</h1>
      <p className="述">开关版本入轨。同键同版本幂等跳过；载荷可为布尔或变体。</p>
      <div className="行">
        <button onClick={async () => { await postFixture("入轨样例"); await 刷(); set讯("已灌入轨样例"); }}>灌入轨样例</button>
        <button className="次" onClick={() => 刷()}>刷新</button>
      </div>
      {讯 && <p className="讯">{讯}</p>}
      {!rows.length ? <div className="空态">尚无版本，先灌入轨样例</div> : (
        <table>
          <thead><tr><th>版本键</th><th>开关键</th><th>版本号</th><th>状态</th><th>入轨时</th></tr></thead>
          <tbody>{rows.map((r) => (
            <tr key={r.版本键}><td>{r.版本键}</td><td>{r.开关键}</td><td>{r.版本号}</td>
            <td><span className="徽章 通">{r.状态}</span></td><td>{r.入轨时}</td></tr>
          ))}</tbody>
        </table>
      )}
    </div>
  );
}
