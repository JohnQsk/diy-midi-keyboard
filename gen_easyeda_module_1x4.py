"""生成方案 B 单模块（1x4 键）嘉立创 EDA 专业版原理图工程。

用 lceda-pro CLI（官方 eda API）无头驱动编辑器，在
`midi_module_1x4.eprj3/`（EPRJ3 文件夹格式工程，对 git 友好）里画出：

- J1（1x8 排母，左）→ J2（1x8 排针，右）8 网直通：pin1-4=ROW1-4，pin5-8=COL1-4
- ROW1-4 各经焊桥 SJ1-4（2P 跳线符号代替）汇到公共线 ROW_sel（装配四选一）
- 4 个按键 SW1-4（Cherry MX 符号 CPG151101S11）：ROW_sel -- 1N4148 -- SW -- COLk，
  二极管阴极（色环端）朝 ROW_sel（COL2ROW），4 键同向

同时导出原理图 PNG 到 `module_1x4_easyeda.png` 并跑一次 sch_Drc。

运行方法（开发机需已安装 lceda-pro，且 chrome-sandbox 权限已修好）：

    python3 gen_easyeda_module_1x4.py

幂等策略：工程目录已存在时直接复用；脚本会先找到（或新 `open --path` 一个）
挂在该工程路径上的无头会话，然后**清空图页内全部器件/导线/文本后重建**，
因此可反复重跑。注意 `open --path` 打开的 EPRJ3 工程与编辑器双向同步，
编辑器保存即落盘。脚本不会 close/stop 任何会话——常驻编辑器进程由用户管理。

真实库器件（立创系统库搜索）：2.54-1*8P母环保(C27438 排母)、直排针2.54mm 1*8P(C49256)、
CPG151101S11（Cherry MX 轴）、1N4148-1(C3646986，DO-35 直插)、1*2P 卧式排针（代替焊桥 SJ）。
注意 J1/J2/D 的选型是为 PCB 排布换过的直插封装，勿改回贴片/其他型号。
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
PNG_PATH = os.path.join(REPO, "module_1x4_easyeda.png")
CLI_TIMEOUT_MS = 300000

# ---------------- 驱动编辑器的 JS（作为 async 函数体注入） ----------------
JS_BUILD = r'''
// ===== 方案B 1x4 模块原理图：幂等重建 =====
const sleep = (ms) => new Promise(r => setTimeout(r, ms));

// 0. 等工程就绪，拿到第一个原理图图页并打开
try { await eda.dmt_Project.waitForReady(); } catch (e) {}
await sleep(2000);
const proj = await eda.dmt_Project.getCurrentProjectInfo();
if (!proj || !proj.data) throw new Error('当前会话未打开工程');
let pageUuid = null;
for (const item of proj.data) {
  if (item.itemType === 'Board' && item.schematic && (item.schematic.page || []).length) {
    pageUuid = item.schematic.page[0].uuid;
    break;
  }
}
if (!pageUuid) throw new Error('工程内没有原理图图页');
await eda.dmt_EditorControl.openDocument(pageUuid);
try { await eda.dmt_EditorControl.waitForDocumentReady(pageUuid); } catch (e) {}
await sleep(1000);

// 1. 清空：全部导线、全部文本、全部“有引脚的”器件（无引脚的是标题栏符号，保留）
const wires0 = await eda.sch_PrimitiveWire.getAll();
if ((wires0 || []).length) await eda.sch_PrimitiveWire.delete(wires0.map(w => w.getState_PrimitiveId()));
const texts0 = await eda.sch_PrimitiveText.getAll();
if ((texts0 || []).length) await eda.sch_PrimitiveText.delete(texts0.map(t => t.getState_PrimitiveId()));
const comps0 = await eda.sch_PrimitiveComponent.getAll();
const delIds = [];
for (const c of comps0 || []) {
  const pins = await eda.sch_PrimitiveComponent.getAllPinsByPrimitiveId(c.getState_PrimitiveId());
  if ((pins || []).length > 0) delIds.push(c.getState_PrimitiveId());
}
if (delIds.length) await eda.sch_PrimitiveComponent.delete(delIds);
await sleep(800);

// 2. 立创系统库取真实器件
async function pick(key, uuid) {
  const r = await eda.lib_Device.search(key, undefined, undefined, undefined, 20, 1);
  const it = (r || []).find(i => i.uuid === uuid);
  if (!it) throw new Error('库器件未找到: ' + key + ' ' + uuid);
  return it;
}
const devJ1 = await pick('2.54-1*8P母环保', '0a4d2569e740414d92321f53f6972245');
const devJ2 = await pick('直排针2.54mm 1*8P', '362f5226d1b94538970a400f15913c45');
const devSW = await pick('CPG151101S11', '61e655f27c534bc6a9b941ac95cd4186');
const devD  = await pick('1N4148-1', '5c09a61a27cf4434b82caebb95d6094a');
const devSJ = await pick('1*2P', '7da6ca4adab84e63a4d8bf11f2bc97bd');

// 3. 放置（坐标单位 10mil；注意渲染时 y 大的一方在图纸上方）
async function put(dev, x, y, rot, mir, des) {
  const c = await eda.sch_PrimitiveComponent.create(dev, x, y, undefined, rot, mir, true, true);
  await eda.sch_PrimitiveComponent.modify(c.getState_PrimitiveId(), { designator: des });
  return c;
}
const J1 = await put(devJ1, 150, 250, 180, false, 'J1');
const J2 = await put(devJ2, 1080, 250, 180, true, 'J2');
const Ds = [], SWs = [], SJs = [];
for (let k = 0; k < 4; k++) {
  Ds.push(await put(devD, 560 + k * 150, 470, 90, false, 'D' + (k + 1)));
  SWs.push(await put(devSW, 560 + k * 150, 580, 90, false, 'SW' + (k + 1)));
  SJs.push(await put(devSJ, 300 + k * 70, 330, 180, false, 'SJ' + (k + 1)));
}

async function pinMap(c) {
  const pins = await eda.sch_PrimitiveComponent.getAllPinsByPrimitiveId(c.getState_PrimitiveId());
  const m = {};
  for (const p of pins || []) m[p.pinNumber] = { x: Math.round(p.x), y: Math.round(p.y), name: p.pinName };
  return m;
}
const P = { J1: await pinMap(J1), J2: await pinMap(J2) };
for (let k = 0; k < 4; k++) {
  P['D' + (k + 1)] = await pinMap(Ds[k]);
  P['SW' + (k + 1)] = await pinMap(SWs[k]);
  P['SJ' + (k + 1)] = await pinMap(SJs[k]);
}
// 二极管方向断言：阴极 pin（名 C 或 K，随库符号而定）的 y 必须更小（渲染时更靠下，朝 ROW_sel 一侧）
for (let k = 1; k <= 4; k++) {
  const d = P['D' + k];
  const cath = (d['1'].name === 'K' || d['1'].name === 'C') ? d['1'] : ((d['2'].name === 'K' || d['2'].name === 'C') ? d['2'] : null);
  const anod = (d['1'].name === 'A') ? d['1'] : d['2'];
  if (!cath || !(cath.y < anod.y)) throw new Error('D' + k + ' 阴极朝向不对: ' + JSON.stringify(d));
}

const ROW = '#c0392b', COL = '#2471a3';

// 4. 主总线：J1.pinN -- J2.pinN 直通，pin1-4=ROW1-4、pin5-8=COL1-4
for (let n = 1; n <= 8; n++) {
  const a = P.J1[String(n)], b = P.J2[String(n)];
  const isRow = n <= 4;
  await eda.sch_PrimitiveWire.create([[a.x, a.y, b.x, b.y]], isRow ? 'ROW' + n : 'COL' + (n - 4), isRow ? ROW : COL, null, null);
}
// ROW_sel 公共线
await eda.sch_PrimitiveWire.create([[280, 420, 1040, 420]], 'ROW_sel', ROW, null, null);

// 5. 焊桥 SJ1-4：上 pin -> 对应 ROWj，下 pin -> ROW_sel（只挂线不短接，四选一如实表达）
for (let k = 0; k < 4; k++) {
  const sj = P['SJ' + (k + 1)];
  const pTop = sj['1'].y < sj['2'].y ? sj['1'] : sj['2'];
  const pBot = sj['1'].y < sj['2'].y ? sj['2'] : sj['1'];
  const rowY = 215 + k * 10;
  await eda.sch_PrimitiveWire.create([[pTop.x, pTop.y, pTop.x, rowY]], undefined, ROW, null, null);
  await eda.sch_PrimitiveWire.create([[pBot.x, pBot.y, pBot.x, 420]], undefined, ROW, null, null);
}

// 6. 键分支：ROW_sel -> D.K(下) ; D.A(上) -> SW ; SW 另一脚 -> 折线绕上 COLk
const dropX = [590, 740, 830, 980];
for (let k = 0; k < 4; k++) {
  const d = P['D' + (k + 1)], sw = P['SW' + (k + 1)];
  const dK = d['1'].y < d['2'].y ? d['1'] : d['2'];
  const dA = d['1'].y < d['2'].y ? d['2'] : d['1'];
  const swNear = sw['1'].y < sw['2'].y ? sw['1'] : sw['2'];  // 靠二极管一侧
  const swFar = sw['1'].y < sw['2'].y ? sw['2'] : sw['1'];
  await eda.sch_PrimitiveWire.create([[dK.x, 420, dK.x, dK.y]], undefined, null, null, null);
  await eda.sch_PrimitiveWire.create([[dA.x, dA.y, dA.x, swNear.y]], undefined, null, null, null);
  const colY = 255 + k * 10, dx = dropX[k];
  await eda.sch_PrimitiveWire.create(
    [[swFar.x, swFar.y, swFar.x, 640], [swFar.x, 640, dx, 640], [dx, 640, dx, colY]],
    undefined, COL, null, null);
}

// 7. 文本标注（原理图注释用英文）
await eda.sch_PrimitiveText.create(590, 780, '1x4 Key Module (Plan B) - Daisy-chain ROW/COL Bus', 0, null, null, 20, true, false, false, 5);
const notes = [
  'J1 (8P female, left) -> J2 (8P male, right): all 8 nets pass straight through (daisy-chain to next module / RP2040-Zero).',
  'pin1-4 = ROW1-4, pin5-8 = COL1-4.',
  'SJ1-4: solder exactly ONE jumper to select this module row (ROW_sel).',
  'Each key: ROW_sel -- 1N4148 -- SW (MX) -- COLk; diode cathode (band) faces ROW_sel (COL2ROW), all 4 identical.',
];
for (let i = 0; i < notes.length; i++) {
  await eda.sch_PrimitiveText.create(100, 640 + i * 25, notes[i], 0, null, null, 12, false, false, false, 1);
}

// 8. 保存（EPRJ3 双向同步落盘）
await eda.sch_Document.save();
await sleep(2000);

// 9. 网络校验：编辑器合并后的命名网络必须正好是 ROW1-4 / COL1-4 / ROW_sel
const wires1 = await eda.sch_PrimitiveWire.getAll();
const nets = {};
for (const w of wires1 || []) {
  const net = w.getState_Net() || '';
  if (net) nets[net.toUpperCase()] = (nets[net.toUpperCase()] || 0) + 1;
}
const expect = ['ROW1', 'ROW2', 'ROW3', 'ROW4', 'COL1', 'COL2', 'COL3', 'COL4', 'ROW_SEL'];
for (const n of expect) if (!nets[n]) throw new Error('缺少网络: ' + n + '，实际: ' + JSON.stringify(nets));
const comps1 = await eda.sch_PrimitiveComponent.getAll();
let devCount = 0;
for (const c of comps1 || []) {
  const pins = await eda.sch_PrimitiveComponent.getAllPinsByPrimitiveId(c.getState_PrimitiveId());
  if ((pins || []).length > 0) devCount++;
}
if (devCount !== 14) throw new Error('器件数量不对: ' + devCount + '（应为 14）');

// 10. DRC
const violations = await eda.sch_Drc.check(true, false, true);
const vlist = Array.isArray(violations) ? violations : [];
if (vlist.length) throw new Error('DRC 未通过: ' + JSON.stringify(vlist));

// 11. 导出 PNG（base64 回传）
const f = await eda.sch_ManufactureData.getPngFile('module_1x4_easyeda', { width: 3000 });
if (!f) throw new Error('getPngFile 返回 undefined');
const buf = new Uint8Array(await f.arrayBuffer());
const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';
let b64 = '';
for (let i = 0; i < buf.length; i += 3) {
  const a = buf[i], b = buf[i + 1], c = buf[i + 2];
  b64 += chars[a >> 2] + chars[((a & 3) << 4) | ((b || 0) >> 4)]
       + (i + 1 < buf.length ? chars[((b & 15) << 2) | ((c || 0) >> 6)] : '=')
       + (i + 2 < buf.length ? chars[c & 63] : '=');
}
return { nets: Object.keys(nets).sort(), devCount, drcViolations: vlist.length, pngName: f.name, pngSize: f.size, pngB64: b64 };
'''

# EPRJ3 最小工程索引（格式参考 github.com/easyeda/easyeda-pro-eprj3-format）；
# 首次 open --path 时编辑器会自动补建 Board1/Schematic1/P1 等并回写该文件。
EPRJ3_INDEX = {
    "name": PROJECT_NAME,
    "owner_uuid": "",
    "creator_uuid": "",
    "created_at": "",
    "updated_at": "",
    "modifier_uuid": "",
    "content": "方案B 1x4键模块级联原理图",
    "archive": False,
    "cbb_project": 0,
    "thumb": "",
    "ticket": 1,
    "g_ticket": 1,
    "boards": [],
    "block_symbol_attrs_groups": {},
    "default_sheet": "",
    "branch_uuid": "",
    "pcb_count": 0,
    "format": "folder",
    "profile": {
        "boards": {}, "schematics": {}, "sheets": {}, "pcbs": {}, "panels": {},
        "blockSymbols": {}, "owner": {"uuid": ""}, "simSchematics": {}, "simulations": {},
    },
    "config": {"defaultSheet": "", "settings": {}},
}


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


def ensure_project_dir():
    index = os.path.join(PROJECT_DIR, PROJECT_NAME + ".eprj3")
    if not os.path.isfile(index):
        os.makedirs(PROJECT_DIR, exist_ok=True)
        with open(index, "w", encoding="utf-8") as fp:
            json.dump(EPRJ3_INDEX, fp, ensure_ascii=False, indent=2)
        print(f"已创建最小 EPRJ3 工程索引: {index}")


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
    for _ in range(10):  # 等工程加载/自动补建图纸
        time.sleep(3)
        if session_has_project(sid):
            return sid
    raise RuntimeError("新会话未能加载工程")


def main():
    ensure_project_dir()
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
        raise RuntimeError(f"编辑器内脚本执行失败: {json.dumps(res, ensure_ascii=False)[:2000]}")
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
    print(f"网络: {', '.join(value.get('nets', []))}")
    print(f"器件: {value.get('devCount')} 个；DRC 违规: {value.get('drcViolations')} 项")
    if value.get("drcViolations"):
        sys.exit(1)


if __name__ == "__main__":
    main()
