import React from "react";
import { Link } from "react-router-dom";
import 核证区 from "../Canary.jsx";

export default function 金丝雀影子道() {
  return (
    <div>
      <h1 className="题">金丝雀影子道</h1>
      <p className="述">
        正式灰度前的试跑。默认取「双道对照（乙）」：一次试跑物化<b>正式票</b>与<b>影子票</b>两张不同票号，
        以同一试跑号配对（同票分路），回读分道记账，核证左右对两路。影子确认<b>不计入</b>正式放量确认，
        影子票<b>无手续不得升正式</b>；串票（影子证号写入正式票号通道）一律失败并旁置。
        也支持「纯影子道（甲）」：发起时传 <code>模式=纯影子</code>，只写影子票，正式已下发不增加。
      </p>
      <div className="行">
        <Link className="次" to="/轨贯验" style={{ alignSelf: "center", color: "var(--信)", fontWeight: 600 }}>
          到贯验页看左右分栏 →
        </Link>
        <Link className="次" to="/回读台" style={{ alignSelf: "center", color: "var(--信)", fontWeight: 600 }}>
          去回读台（分道） →
        </Link>
      </div>
      <核证区 showActions title="试跑 · 分路回读 · 核证 · 放量闸" />
    </div>
  );
}
