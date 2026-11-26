import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { get, postFixture } from "../api.js";

export default function 下发票() {
  const [rows, setRows] = useState([]);
  const [讯, set讯] = useState("");
  const 刷 = async () => setRows(await get("/下发票"));
  useEffect(() => { 刷().catch((e) => set讯(String(e))); }, []);
  return (
    <div>
      <h1 className="题">下发票</h1>
      <p className="述">版本对分桶的一次灰度下发。票号幂等；成功后版本态变「灰度中」。</p>
      <div className="行">
        <button onClick={async () => { await postFixture("下发样例"); await 刷(); set讯("已灌下发样例"); }}>灌下发样例</button>
        <button className="次" onClick={() => 刷()}>刷新</button>
        <Link className="次" to="/金丝雀影子道" data-testid="去发起试跑"
          style={{ alignSelf: "center", color: "var(--信)", fontWeight: 600 }}>
          发起金丝雀试跑（正式票 + 影子票分路） →
        </Link>
      </div>
      {讯 && <p className="讯">{讯}</p>}
      {!rows.length ? <div className="空态">尚无下发票（需先入轨+分桶）</div> : (
        <table>
          <thead><tr><th>票号</th><th>版本键</th><th>桶键</th><th>状态</th><th>下发时</th></tr></thead>
          <tbody>{rows.map((r) => (
            <tr key={r.票号}><td>{r.票号}</td><td>{r.版本键}</td><td>{r.桶键}</td>
            <td><span className="徽章 通">{r.状态}</span></td><td>{r.下发时}</td></tr>
          ))}</tbody>
        </table>
      )}
    </div>
  );
}
