"""生成方案 B 单模块（1x4 键）嘉立创 EDA 专业版 PCB。

用 lceda-pro CLI（官方 eda API）无头驱动编辑器，在 `midi_module_1x4.eprj3/`
工程的 PCB 图页里完成布局布线。依赖 `gen_easyeda_module_1x4.py` 已生成原理图
（先跑原理图生成器，再跑本脚本）。

板型与布局（板内坐标 mil，y 向上）：

- 双层板 92.5x40mm（3640x1575mil），四角 M3 NPTH（Ø3.2mm）
- 4 个 MX 轴 SW1-4，键心距 19.05mm（750mil），键心 x = 695+k*750（= 17.653+k*19.05mm），
  两侧各留 320mil（8.13mm）边距放级联接口；代价：板宽不再是键距整数倍，
  多模块并排时接缝处键距约 35.3mm（正常 19.05mm），接缝有明显缝隙
- MX 用 5 孔封装（2 信号脚 + 中心柱 NPTH Ø4mm + 定位柱 NPTH Ø1.7mm x2）：
  脚本会把工程库里的 CPG151101S11 封装改造成 5 孔直插（原封装是热插拔轴座，
  还会顺带删掉轴座遗留的铜皮 FILL / 13 层槽圆，否则 DRC 报 Slot Region 违规），
  并删除重建 SW1-4 使实例几何刷新
- D1-4：1N4148 DO-35 卧式，阴极（色环端）在右、朝 ROW_SEL 汇流（COL2ROW）
- J1/J2（1x8P）竖放在左右两侧板边中央（旋转 90°，引脚沿 Y）：
  实际焊接用 90° 弯针公头（焊盘与普通直针相同，封装不用换），
  级联用 8P F-F 杜邦线从侧面水平对插
- SJ1-4 焊桥（顶层 SMD 盘）在板下部中央；每块板只焊一个选行
- 布线：8 条直通总线底层横走（30mil 间距，y=75+30i 按 J1 焊盘实测自适应分配），
  两侧扇出顶层 90° 下接总线；ROW_SEL 全顶层：SJ pad2 -> y=45 汇集走廊 ->
  x=1820 上升通道 -> y=1350 顶层汇流 -> 各二极管阴极；键链（COL->SW pin1）顶层走线；
  线宽 16mil（0.41mm），过孔 12/20mil（DRC 按孔+盘=Ø32mil 有效直径算间距）
- 网络名与原理图一致：ROW1-4 / COL1-4 / ROW_SEL / $1N23-26（键分支自动命名）

脚本幂等：先清掉全部走线/过孔/丝印/板框/安装孔再重建，可反复重跑。
结束时跑一次 pcb_Drc（必须 0 违规，否则报错退出）并导出渲染 PNG 到
`module_1x4_easyeda_pcb.png`。

运行方法（开发机需已安装 lceda-pro）：

    python3 gen_easyeda_module_1x4.py        # 先生成原理图
    python3 gen_easyeda_module_1x4_pcb.py    # 再生成本 PCB

已踩过的 API 坑（改动时注意）：
- pcb_PrimitiveLine.create 不支持板框层(11)，板框用 pcb_PrimitivePolyline 画
- 后创建的过孔落在已有走线上不会自动并入连接图（DRC Connection Error），
  需要在过孔创建后再补一段同网短走线"缝合"
- 元件实例缓存封装几何：改完库内封装必须删除重建元件，实例才会刷新
- 封装编辑器里 hole 字段单位是 mil，PCB 图页里读回是 10mil
"""
import base64
import json
import os
import subprocess
import sys
import tempfile
import time

REPO = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.join(REPO, "midi_module_1x4.eprj3")
PROJECT_NAME = "midi_module_1x4"
PNG_PATH = os.path.join(REPO, "module_1x4_easyeda_pcb.png")
CLI_TIMEOUT_MS = 300000

# ---------------- 驱动编辑器的 JS（作为 async 函数体注入） ----------------
JS_BUILD = r'''
const sleep = (ms) => new Promise(r => setTimeout(r, ms));
try { await eda.dmt_Project.waitForReady(); } catch (e) {}
await sleep(2000);
const proj = await eda.dmt_Project.getCurrentProjectInfo();
if (!proj || !proj.data) throw new Error('当前会话未打开工程');
let pcbUuid = null;
for (const item of proj.data) { if (item.itemType === 'Board') pcbUuid = item.pcb.uuid; }
if (!pcbUuid) throw new Error('工程内没有 PCB 图页');
await eda.dmt_EditorControl.openDocument(pcbUuid);
try { await eda.dmt_EditorControl.waitForDocumentReady(pcbUuid); } catch (e) {}
await sleep(1000);

// ===== A. 先 importChanges，确保 PCB 上有全部 14 个器件 =====
await eda.pcb_Document.importChanges(undefined, true);
await sleep(2000);

// ===== B. MX 封装改造为 5 孔直插（幂等） =====
const compsA = await eda.pcb_PrimitiveComponent.getAll();
let fpRef = null;
for (const c of compsA || []) {
  if (/^SW[1-4]$/.test(c.getState_Designator())) { fpRef = c.getState_Footprint(); break; }
}
if (!fpRef || !fpRef.uuid) throw new Error('PCB 上找不到 SW1-4（importChanges 失败？）');
const projLibAlias = 'project';  // getProjectLibraryUuid() 无头模式下只返回别名 'project'，编辑类 API 需要真实 uuid
// 优先复用工程库里已有的改造封装
let fpUuid = null, projLibUuid = null;
for (const key of ['MX5P_1x4MODULE', 'CPG151101S11']) {
  const r = await eda.lib_Footprint.search(key, projLibAlias, undefined, 5, 1);
  if ((r || []).length) { fpUuid = r[0].uuid; projLibUuid = r[0].libraryUuid || null; break; }
}
if (!projLibUuid) {
  // 从器件封装引用推断工程库真实 uuid（取第一个非系统库的引用）
  const sysLibUuid = await eda.lib_LibrariesList.getSystemLibraryUuid();
  for (const c of compsA || []) {
    const f = c.getState_Footprint();
    if (f && f.libraryUuid && f.libraryUuid !== sysLibUuid) { projLibUuid = f.libraryUuid; break; }
  }
  if (!projLibUuid) throw new Error('无法确定工程库 uuid');
}
if (!fpUuid) {  // 工程库没有：从器件引用的封装复制进来
  fpUuid = await eda.lib_Footprint.copy(fpRef.uuid, fpRef.libraryUuid, projLibUuid, undefined, 'MX5P_1x4MODULE');
  if (!fpUuid) throw new Error('封装复制到工程库失败');
}
await eda.lib_Footprint.openInEditor(fpUuid, projLibUuid);
await sleep(2000);
// B1. 删掉轴座遗留的全部 FILL 铜皮与 13 层折线（槽圆）
const fills0 = await eda.pcb_PrimitiveFill.getAll();
if ((fills0 || []).length) await eda.pcb_PrimitiveFill.delete(fills0.map(f => f.getState_PrimitiveId()));
const pls0 = await eda.pcb_PrimitivePolyline.getAll();
const pl13 = (pls0 || []).filter(p => p.getState_Layer() === 13).map(p => p.getState_PrimitiveId());
if (pl13.length) await eda.pcb_PrimitivePolyline.delete(pl13);
// B2. 焊盘归一化：信号脚 TH（Ø1.5mm 孔），3 个 NPTH 柱孔
const padsB = await eda.pcb_PrimitivePad.getAll();
const sigPos = { '1': [-150, -100], '2': [100, -200] };
for (const p of padsB || []) {
  const num = p.getState_PadNumber();
  if (num === '1' || num === '2') {
    await eda.pcb_PrimitivePad.modify(p.getState_PrimitiveId(), {
      layer: 12, x: sigPos[num][0], y: sigPos[num][1],
      pad: ['ELLIPSE', 80, 80], hole: ['ROUND', 59], metallization: true });
  }
}
// NPTH 目标：中心柱 Ø4mm（铜环 180mil）、定位柱 Ø1.7mm（铜环 88mil）
const npthTarget = [[0, 0, 180, 157.5], [-200, 0, 88, 67], [200, 0, 88, 67]];
const padsB2 = await eda.pcb_PrimitivePad.getAll();
const mech = (padsB2 || []).filter(p => p.getState_PadNumber() === '');
const used = new Set();
for (const p of mech) {
  // 找最近目标
  let best = -1, bd = 1e9;
  for (let i = 0; i < 3; i++) {
    if (used.has(i)) continue;
    const d = Math.abs(p.getState_X() - npthTarget[i][0]) + Math.abs(p.getState_Y() - npthTarget[i][1]);
    if (d < bd) { bd = d; best = i; }
  }
  if (best >= 0 && bd < 100) {
    used.add(best);
    const t = npthTarget[best];
    await eda.pcb_PrimitivePad.modify(p.getState_PrimitiveId(), {
      layer: 12, x: t[0], y: t[1], pad: ['ELLIPSE', t[2], t[2]], hole: ['ROUND', t[3]], metallization: false });
  } else {
    await eda.pcb_PrimitivePad.delete(p.getState_PrimitiveId());
  }
}
for (let i = 0; i < 3; i++) {
  if (used.has(i)) continue;
  const t = npthTarget[i];
  await eda.pcb_PrimitivePad.create(12, '', t[0], t[1], 0, ['ELLIPSE', t[2], t[2]], '', ['ROUND', t[3]], 0, 0, 0, false, 0);
}
await sleep(500);
await eda.pcb_Document.save();
await sleep(1500);

// ===== C. 删除重建 SW1-4（元件实例缓存封装几何，必须重建才刷新） =====
await eda.dmt_EditorControl.openDocument(pcbUuid);
try { await eda.dmt_EditorControl.waitForDocumentReady(pcbUuid); } catch (e) {}
await sleep(1000);
const BX = 500, BY = -2600;
const X = v => BX + v, Y = v => BY + v;
const xk = k => 695 + k * 750;
const compsC = await eda.pcb_PrimitiveComponent.getAll();
const delSW = (compsC || []).filter(c => /^SW[1-4]$/.test(c.getState_Designator())).map(c => c.getState_PrimitiveId());
if (delSW.length) await eda.pcb_PrimitiveComponent.delete(delSW);
await sleep(500);
for (let k = 0; k < 4; k++) {
  const it = await eda.lib_Footprint.get(fpUuid, projLibUuid);
  it.libraryUuid = projLibUuid;
  const c = await eda.pcb_PrimitiveComponent.create(it, 1, X(xk(k)), Y(787), 0, false);
  await eda.pcb_PrimitiveComponent.modify(c.getState_PrimitiveId(), { designator: 'SW' + (k + 1) });
}
await sleep(500);
await eda.pcb_Document.importChanges(undefined, true);   // 恢复焊盘网络关联
await sleep(2000);
await eda.pcb_Document.save();
await sleep(1000);

// ===== D. 布局布线（幂等：先清后建） =====
const TOP = 1, BOT = 2, SILK = 3, OUTLINE = 11, MULTI = 12;
const W = 16;
const BOARD_W = 3640, BOARD_H = 1575;
const SJCX = k => 1150 + k * 150;
const MOUNT = [[120, 120], [3520, 120], [120, 1455], [3520, 1455]];

const del = async (getter, deleter) => {
  const items = await getter();
  if (items && items.length) await deleter(items.map(i => i.getState_PrimitiveId()));
};
await del(() => eda.pcb_PrimitiveLine.getAll(), ids => eda.pcb_PrimitiveLine.delete(ids));
await del(() => eda.pcb_PrimitiveVia.getAll(), ids => eda.pcb_PrimitiveVia.delete(ids));
await del(() => eda.pcb_PrimitivePolyline.getAll(), ids => eda.pcb_PrimitivePolyline.delete(ids));
await del(() => eda.pcb_PrimitiveString.getAll(), ids => eda.pcb_PrimitiveString.delete(ids));
const pads0 = await eda.pcb_PrimitivePad.getAll();
// 游离焊盘=安装孔；历代板宽的右下角 x 不同（2880/3380/3420/3520），全部纳入删除集合
const mountSet = new Set();
for (const mx of [120, 2880, 3380, 3420, 3520]) for (const my of [120, 1455]) mountSet.add(X(mx) + ',' + Y(my));
const freePads = (pads0 || []).filter(p => mountSet.has(p.getState_X() + ',' + p.getState_Y())).map(p => p.getState_PrimitiveId());
if (freePads.length) await eda.pcb_PrimitivePad.delete(freePads);

const L = (net, layer, x1, y1, x2, y2) => eda.pcb_PrimitiveLine.create(net, layer, X(x1), Y(y1), X(x2), Y(y2), W, false);
const viaList = [];
const V = async (net, x, y) => { await eda.pcb_PrimitiveVia.create(net, X(x), Y(y), 12, 20); viaList.push([net, x, y]); };

// D1. 摆位（J1/J2 旋转 90° 竖放于左右板边中央）
const compsD = await eda.pcb_PrimitiveComponent.getAll();
for (const c of compsD || []) {
  const des = c.getState_Designator();
  let p = null, m, rot = 0;
  if ((m = des.match(/^SW([1-4])$/))) p = [xk(+m[1] - 1), 787];
  else if ((m = des.match(/^D([1-4])$/))) p = [xk(+m[1] - 1), 1217];
  else if (des === 'J1') { p = [150, 787]; rot = 90; }
  else if (des === 'J2') { p = [3490, 787]; rot = 90; }
  else if ((m = des.match(/^SJ([1-4])$/))) p = [SJCX(+m[1] - 1), 400];
  if (p) await eda.pcb_PrimitiveComponent.modify(c.getState_PrimitiveId(), { x: X(p[0]), y: Y(p[1]), rotation: rot });
}
await sleep(1000);

// D2. 板框（11 层只支持折线）
const ol = eda.pcb_MathPolygon.createPolygon([X(0), Y(0), 'L', X(BOARD_W), Y(0), 'L', X(BOARD_W), Y(BOARD_H), 'L', X(0), Y(BOARD_H), 'L', X(0), Y(0)]);
await eda.pcb_PrimitivePolyline.create('', OUTLINE, ol, 6, false);

// D3. 安装孔 M3 NPTH
for (const [hx, hy] of MOUNT)
  await eda.pcb_PrimitivePad.create(MULTI, '', X(hx), Y(hy), 0, ['ELLIPSE', 150, 150], '', ['ROUND', 126], 0, 0, 0, false, 0);

// D4. 8 条直通总线 J1.pinN -> J2.pinN
// 实测 J1/J2 焊盘坐标，按 y 升序分配底层总线 y=75+30i；两侧顶层扇出 90° 下接
// （左 riser x=220+30i、右 riser x=3420-30i，保证扇出不交叉且与相邻过孔/安装孔留够间距）
const jPads = {};
for (const c of compsD || []) {
  const des = c.getState_Designator();
  if (des !== 'J1' && des !== 'J2') continue;
  const pins = await eda.pcb_PrimitiveComponent.getAllPinsByPrimitiveId(c.getState_PrimitiveId());
  jPads[des] = (pins || []).map(p => ({ net: p.net, x: p.x - BX, y: p.y - BY })).sort((a, b) => a.y - b.y);
}
if (!jPads.J1 || jPads.J1.length !== 8 || !jPads.J2 || jPads.J2.length !== 8)
  throw new Error('J1/J2 焊盘读取失败: ' + JSON.stringify(Object.keys(jPads)));
const busY = {};
for (let i = 0; i < 8; i++) {
  const n1 = jPads.J1[i].net, n2 = jPads.J2[i].net;
  if (n1 !== n2) throw new Error(`J1/J2 第 ${i + 1} 个焊盘(按 y 升序)网络不一致: ${n1} vs ${n2}（两侧旋转方向需一致）`);
  busY[n1] = 75 + 30 * i;
}
for (let i = 0; i < 8; i++) {
  const p1 = jPads.J1[i], p2 = jPads.J2[i], net = p1.net, by = busY[net];
  const rx = 220 + 30 * i, qx = 3420 - 30 * i;
  await L(net, TOP, p1.x, p1.y, rx, p1.y);
  await L(net, TOP, rx, p1.y, rx, by);
  await V(net, rx, by);
  await L(net, BOT, rx, by, qx, by);
  await L(net, TOP, qx, by, qx, p2.y);
  await L(net, TOP, qx, p2.y, p2.x, p2.y);
  await V(net, qx, by);
}

// D5. ROW_SEL（全顶层）：SJ pad2 -> y=45 走廊 -> x=1820 上升通道 -> y=1350 汇流 -> 各二极管阴极
for (let k = 0; k < 4; k++) {
  const sx = SJCX(k) + 50;
  await L('ROW_SEL', TOP, sx, 337, sx, 45);
}
await L('ROW_SEL', TOP, SJCX(0) + 50, 45, 1820, 45);
await L('ROW_SEL', TOP, 1820, 45, 1820, 1350);
await L('ROW_SEL', TOP, xk(0) + 153.5, 1350, xk(3) + 153.5, 1350);
for (let k = 0; k < 4; k++)
  await L('ROW_SEL', TOP, xk(k) + 153.5, 1350, xk(k) + 153.5, 1217);

// D6. SJ pad1 -> ROWk 总线：顶层 stub 直下 + 过孔（SJ 焊盘 y 跨 337..463，从底边 337 起线）
for (let k = 0; k < 4; k++) {
  const net = 'ROW' + (k + 1), px = SJCX(k) - 50, by = busY[net];
  await L(net, TOP, px, 337, px, by);
  await V(net, px, by);
}

// D7. 键链：COLk 总线 -> SW pin1（顶层）；SW pin2 -> 二极管阳极（$1N 分支，从焊盘实读）
const BR = [], P1 = [];
for (const c of compsD || []) {
  const m = c.getState_Designator().match(/^SW([1-4])$/);
  if (!m) continue;
  const pins = await eda.pcb_PrimitiveComponent.getAllPinsByPrimitiveId(c.getState_PrimitiveId());
  for (const p of pins || []) {
    if (p.padNumber === '1') P1[+m[1] - 1] = p.net;
    if (p.padNumber === '2') BR[+m[1] - 1] = p.net;
  }
}
if (BR.length !== 4 || BR.some(n => !n)) throw new Error('键分支网络读取失败: ' + JSON.stringify(BR));
for (let k = 0; k < 4; k++)
  if (P1[k] !== 'COL' + (k + 1)) throw new Error(`SW${k + 1} pin1 网络异常: ${P1[k]}（应为 COL${k + 1}）`);
const CHAIN_VX = [500, 1150, 2250, 3000];
for (let k = 0; k < 4; k++) {
  const cx = xk(k), net = 'COL' + (k + 1), by = busY[net], vx = CHAIN_VX[k], px = cx - 150;
  await V(net, vx, by);
  await L(net, TOP, vx, by, vx, 520);
  await L(net, TOP, vx, 520, px, 520);
  await L(net, TOP, px, 520, px, 687);
  const segs = [[cx - 153.5, 1217, cx - 153.5, 1140], [cx - 153.5, 1140, cx + 123, 1140], [cx + 123, 1140, cx + 123, 640], [cx + 123, 640, cx + 100, 640], [cx + 100, 640, cx + 100, 587]];
  for (const [x1, y1, x2, y2] of segs) await L(BR[k], TOP, x1, y1, x2, y2);
}

// D7.5 连接缝合：后放的过孔不会自动并入已有铜皮连接图，补同网短段
for (const [net, x, y] of viaList) {
  await L(net, TOP, x - 8, y, x + 8, y);
  await L(net, BOT, x - 8, y, x + 8, y);
}

// D8. 丝印
async function silk(x, y, text, size, align, rot) {
  await eda.pcb_PrimitiveString.create(SILK, X(x), Y(y), text, 'default', size || 40, Math.max(5, Math.round((size || 40) / 7)), align === undefined ? 5 : align, rot || 0, false, 0, false, false);
}
await silk(1820, 1500, 'MIDI 1x4 Key Module', 55);
await silk(200, 1300, 'J1: 1-4=ROW1-4 5-8=COL1-4', 24, 4);
await silk(3440, 1300, 'J2: 1-4=ROW1-4 5-8=COL1-4', 24, 6);
await silk(1820, 320, 'SJ1-4: solder ONE = ROW1-4', 28);
for (let k = 0; k < 4; k++) await silk(xk(k), 1435, 'K' + (k + 1), 40);
for (let k = 0; k < 4; k++) await silk(SJCX(k), 520, 'SJ' + (k + 1), 26);
await silk(200, 430, '1', 28, 4);
await silk(3440, 430, '1', 28, 6);

await eda.pcb_Document.save();
await sleep(2000);

// ===== E. DRC =====
const violations = await eda.pcb_Drc.check(true, false, true);
const vlist = Array.isArray(violations) ? violations : [];
if (vlist.length) throw new Error('PCB DRC 未通过: ' + JSON.stringify(vlist).slice(0, 3000));

// ===== F. 导出渲染 PNG（base64 回传） =====
const tabId = await eda.dmt_EditorControl.openDocument(pcbUuid);
try { await eda.dmt_EditorControl.zoomToAllPrimitives(); } catch (e) {}
await sleep(1500);
const blob = await eda.dmt_EditorControl.getCurrentRenderedAreaImage(tabId);
if (!blob) throw new Error('getCurrentRenderedAreaImage 返回 undefined');
const buf = new Uint8Array(await blob.arrayBuffer());
const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';
let b64 = '';
for (let i = 0; i < buf.length; i += 3) {
  const a = buf[i], b = buf[i + 1], c = buf[i + 2];
  b64 += chars[a >> 2] + chars[((a & 3) << 4) | ((b || 0) >> 4)]
       + (i + 1 < buf.length ? chars[((b & 15) << 2) | ((c || 0) >> 6)] : '=')
       + (i + 2 < buf.length ? chars[c & 63] : '=');
}
const nl = (await eda.pcb_PrimitiveLine.getAll() || []).length;
const nv = (await eda.pcb_PrimitiveVia.getAll() || []).length;
return { lines: nl, vias: nv, drcViolations: vlist.length, pngSize: blob.size, pngB64: b64, fpUuid };
'''


def run_cli(args, timeout_s=320):
    """调 lceda-pro，过滤 libDirs 噪音行，返回解析后的 JSON。"""
    out = subprocess.run(
        ["lceda-pro"] + args,
        capture_output=True, text=True, timeout=timeout_s,
    )
    lines = [l for l in out.stdout.splitlines() if "libdirs" not in l.lower()]
    text = "\n".join(lines).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        raise RuntimeError(f"lceda-pro 输出不是 JSON:\n{text}\nstderr: {out.stderr[:500]}")


def session_has_project(sid):
    """探测会话是否真的加载了工程（仅有 path 记录不代表已加载）。"""
    probe = "const p = await eda.dmt_Project.getCurrentProjectInfo(); return !!(p && p.data);"
    try:
        res = run_cli(["invoke", "--session", sid, "--ext-uuid", "eda", "--code", probe])
    except Exception:
        return False
    return bool(res.get("ok") and res.get("value"))


def find_or_open_session():
    lst = run_cli(["session", "list"])
    for s in lst.get("value") or []:
        if s.get("path") == PROJECT_DIR and s.get("status") == "alive" and session_has_project(s["sessionId"]):
            print(f"复用已挂工程的会话: {s['sessionId']}")
            return s["sessionId"]
    res = run_cli(["open", "--path", PROJECT_DIR, "--headless", "true"])
    sid = (res.get("value") or {}).get("sessionId")
    if not sid:
        raise RuntimeError(f"open --path 失败: {res}")
    print(f"已打开无头会话: {sid}")
    for _ in range(10):  # 等工程加载
        time.sleep(3)
        if session_has_project(sid):
            return sid
    raise RuntimeError("新会话未能加载工程")


def main():
    if not os.path.isfile(os.path.join(PROJECT_DIR, PROJECT_NAME + ".eprj3")):
        raise RuntimeError(f"工程不存在: {PROJECT_DIR}，请先运行 gen_easyeda_module_1x4.py")
    session = find_or_open_session()

    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as fp:
        fp.write(JS_BUILD)
        js_path = fp.name
    try:
        res = run_cli([
            "invoke", "--session", session, "--ext-uuid", "eda",
            "--code-file", js_path, "--timeout", str(CLI_TIMEOUT_MS),
        ])
    finally:
        os.unlink(js_path)

    if not res.get("ok"):
        raise RuntimeError(f"编辑器内脚本执行失败: {json.dumps(res, ensure_ascii=False)[:3000]}")
    value = res.get("value") or {}
    png_b64 = value.get("pngB64")
    if not png_b64:
        raise RuntimeError(f"未拿到 PNG 数据: {json.dumps(value, ensure_ascii=False)[:500]}")
    data = base64.b64decode(png_b64)
    if len(data) != value.get("pngSize"):
        raise RuntimeError("PNG 字节数校验失败")
    with open(PNG_PATH, "wb") as fp:
        fp.write(data)

    print(f"工程: {PROJECT_DIR}")
    print(f"PNG:  {PNG_PATH} ({len(data)} 字节)")
    print(f"走线: {value.get('lines')} 条；过孔: {value.get('vias')} 个；DRC 违规: {value.get('drcViolations')} 项")
    if value.get("drcViolations"):
        sys.exit(1)


if __name__ == "__main__":
    main()
