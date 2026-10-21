"""生成 16 键单排钢琴布局 MIDI 键盘 PCB：midi_matrix_4x4.kicad_pcb + .kicad_pro + 预览 PNG。

物理布局：16 个 Cherry MX 轴（PCB 安装 5 孔封装）按 19.05mm 键心距排成一排，
K0..K15 从左到右 = 音符 60..75（C4..D#5 半音阶）。
电气连接仍是 4x4 矩阵（COL2ROW，每键串 1N4148，阴极/色环朝行）：
键 i 属于 ROW(i//4) + COL(i%4)，即 K0-3=ROW1、K4-7=ROW2 …… COL1..4 循环。
二极管横放在键上方空隙带；8 条总线（4 行 + 4 列）在键下方 B.Cu 横走，
左侧 1x8 竖排针 J1 与总线同高直连：pin1..4 = ROW1..4 (GP1..GP4)，pin5..8 = COL1..4 (GP5..GP8)。
双层板，共 32 个过孔（每键行/列各一落线）。板框 316x66mm（长条板，超出嘉立创免费档）。
所有封装内嵌，KiCad 8+ 直接打开即可（网络类定义写在 .kicad_pro 的 net_settings 里）。
运行：python3 gen_kicad_pcb_4x4.py
"""
import json
import uuid

PROJ = "midi_matrix_4x4"

# ---------- 几何常量（mm） ----------
P = 19.05                 # 键心距（0.75 英寸标准）
X0, YK = 20.0, 30.0       # 最左键中心 / 键排 y
TRACK = 0.8               # 线宽
VIA_D, VIA_DRILL = 1.2, 0.6
DIODE_DY = -9.525         # 二极管在键上方空隙带（相对键心）
BUS_Y0 = 43.0             # 第 1 条总线 y，8 条总线间距 2.54（与排针节距一致）
HDR_X = 8.0               # 竖排针 x，pin k 与总线 k 同高直连
# MX 轴焊盘相对键心：pin1(-3.81, 2.54)、pin2(2.54, 5.08)；
# 中心柱 NPTH 4.0@(0,0)，定位柱 NPTH 1.7@(±5.08, 0)

ROW_NET = [f"ROW{i + 1}" for i in range(4)]
COL_NET = [f"COL{i + 1}" for i in range(4)]
KNET = [f"Net-K{k}" for k in range(16)]
NETS = ROW_NET + COL_NET + KNET
NET_ID = {n: i + 1 for i, n in enumerate(NETS)}
BUS_NET = ROW_NET + COL_NET  # 总线 k (y=BUS_Y0+k*2.54) ←→ 排针 pin k+1

NOTES = ["C4", "C#4", "D4", "D#4", "E4", "F4", "F#4", "G4",
         "G#4", "A4", "A#4", "B4", "C5", "C#5", "D5", "D#5"]  # 音符 60..75


def u():
    return str(uuid.uuid4())


def f(v):
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return s if s else "0"


def bus_y(k):
    return BUS_Y0 + k * PIN_P


PIN_P = 2.54

# ---------- 收集走线 / 过孔 / 丝印 ----------
segs = []      # (x1, y1, x2, y2, layer, net)
vias = []      # (x, y, net)
gr_texts = []  # (content, x, y, size)

# 供预览用的图元
pads = []      # (x, y, w, h)
npths = []     # (x, y, drill)
diodes = []    # (cx, cy) 水平放置，左侧为阴极
switches = []  # (cx, cy)


def seg(x1, y1, x2, y2, layer, net):
    segs.append((x1, y1, x2, y2, layer, net))


# ---------- 16 个键（单排，左→右 K0..K15） ----------
bus_end = [HDR_X] * 8  # 每条总线的最右端 x（随落线更新）
for i in range(16):
    ri, ci = i // 4, i % 4
    x, y = X0 + P * i, YK
    switches.append((x, y))
    diodes.append((x + 4, y + DIODE_DY))
    npths += [(x, y, 4.0), (x - 5.08, y, 1.7), (x + 5.08, y, 1.7)]
    pads.append((x - 3.81, y + 2.54, 2.5, 2.5))        # MX pin1 → 二极管
    pads.append((x + 2.54, y + 5.08, 2.5, 2.5))        # MX pin2 → 行线
    pads.append((x + 0.19, y + DIODE_DY, 1.6, 1.6))    # 二极管阴极
    pads.append((x + 7.81, y + DIODE_DY, 1.6, 1.6))    # 二极管阳极
    # MX pin1 → 二极管阴极（F.Cu：左横 → 上竖 → 45°，绕开中心柱与定位柱孔）
    seg(x - 3.81, y + 2.54, x - 6.8, y + 2.54, "F.Cu", KNET[i])
    seg(x - 6.8, y + 2.54, x - 6.8, y - 2.535, "F.Cu", KNET[i])
    seg(x - 6.8, y - 2.535, x + 0.19, y + DIODE_DY, "F.Cu", KNET[i])
    # MX pin2 → 行总线（F.Cu 下落 + 过孔）
    seg(x + 2.54, y + 5.08, x + 2.54, bus_y(ri), "F.Cu", ROW_NET[ri])
    vias.append((x + 2.54, bus_y(ri), ROW_NET[ri]))
    bus_end[ri] = max(bus_end[ri], x + 2.54)
    # 二极管阳极 → 列总线（F.Cu 下落 + 过孔）
    seg(x + 7.81, y + DIODE_DY, x + 7.81, bus_y(4 + ci), "F.Cu", COL_NET[ci])
    vias.append((x + 7.81, bus_y(4 + ci), COL_NET[ci]))
    bus_end[4 + ci] = max(bus_end[4 + ci], x + 7.81)
    gr_texts.append((f"K{i}", x, y - 13, 1.0))

# ---------- 8 条总线（B.Cu 横线，左端直接进排针焊盘） ----------
for k, net in enumerate(BUS_NET):
    seg(HDR_X, bus_y(k), bus_end[k], bus_y(k), "B.Cu", net)
    pads.append((HDR_X, bus_y(k), 1.8, 1.8))
    gr_texts.append((str(k + 1), 5.3, bus_y(k), 0.8))

gr_texts.append(("16-key piano MIDI keyboard (4x4 matrix, COL2ROW)", 160, 5.5, 1.6))
gr_texts.append(("J1: pin1-4=ROW1-4/GP1-4  pin5-8=COL1-4/GP5-8   K0..K15 -> notes 60..75",
                 160, 66.3, 1.2))

HOLES = [(6, 6), (312, 6), (6, 64.5), (312, 64.5)]
EDGE = (2, 2, 318, 68)  # x1, y1, x2, y2

# ---------- KiCad 文件输出 ----------
parts = []


def prop(name, value, x, y, layer, hide=True):
    h = " (hide yes)" if hide else ""
    return (f'    (property "{name}" "{value}" (at {f(x)} {f(y)} 0) (layer "{layer}"){h} '
            f'(uuid "{u()}") (effects (font (size 1 1) (thickness 0.15))))')


def fp_line(x1, y1, x2, y2, layer="F.SilkS", w=0.12):
    return (f'    (fp_line (start {f(x1)} {f(y1)}) (end {f(x2)} {f(y2)}) '
            f'(stroke (width {w}) (type solid)) (layer "{layer}") (uuid "{u()}"))')


def fp_pad(num, x, y, size, drill, net, shape="circle"):
    n = f' (net {NET_ID[net]} "{net}")' if net else ""
    kind = "thru_hole" if net else "np_thru_hole"
    return (f'    (pad "{num}" {kind} {shape} (at {f(x)} {f(y)}) (size {f(size)} {f(size)}) '
            f'(drill {f(drill)}) (layers "*.Cu" "*.Mask"){n} (uuid "{u()}"))')


def emit_switch(i, x, y):
    lines = [f'  (footprint "diy:SW_Cherry_MX_1U" (layer "F.Cu")', f'    (uuid "{u()}")',
             f'    (at {f(x)} {f(y)})',
             '    (descr "Cherry MX 1u PCB mount: pin1=(-3.81,2.54) pin2=(2.54,5.08)")',
             '    (attr through_hole)',
             prop("Reference", f"SW{i + 1}", 0, -8.5, "F.SilkS"),
             prop("Value", f"K{i} ({NOTES[i]})", 0, 8.5, "F.Fab")]
    for x1, y1, x2, y2 in ((-7, -7, 7, -7), (7, -7, 7, 7), (7, 7, -7, 7), (-7, 7, -7, -7)):
        lines.append(fp_line(x1, y1, x2, y2))
    lines.append(fp_pad("1", -3.81, 2.54, 2.5, 1.5, KNET[i], "rect"))
    lines.append(fp_pad("2", 2.54, 5.08, 2.5, 1.5, ROW_NET[i // 4]))
    lines.append(fp_pad("", 0, 0, 4.0, 4.0, None))       # 中心柱
    lines.append(fp_pad("", -5.08, 0, 1.7, 1.7, None))   # 定位柱
    lines.append(fp_pad("", 5.08, 0, 1.7, 1.7, None))
    lines.append("  )")
    return "\n".join(lines)


def emit_diode(i, x, y):
    lines = [f'  (footprint "diy:D_DO-35" (layer "F.Cu")', f'    (uuid "{u()}")',
             f'    (at {f(x)} {f(y)})',
             '    (descr "1N4148 DO-35 horizontal, pad1=cathode (band)")',
             '    (attr through_hole)',
             prop("Reference", f"D{i + 1}", 0, -2.2, "F.SilkS"),
             prop("Value", "1N4148", 0, 2.2, "F.Fab")]
    for x1, y1, x2, y2 in ((-3, 0, -2, 0), (2, 0, 3, 0),      # 引出线
                           (-2, -0.9, 2, -0.9), (2, -0.9, 2, 0.9),
                           (2, 0.9, -2, 0.9), (-2, 0.9, -2, -0.9)):
        lines.append(fp_line(x1, y1, x2, y2))
    lines.append(fp_line(-1.3, -0.9, -1.3, 0.9, w=0.35))      # 阴极色环标记
    lines.append(fp_pad("1", -3.81, 0, 1.6, 0.8, KNET[i], "rect"))
    lines.append(fp_pad("2", 3.81, 0, 1.6, 0.8, COL_NET[i % 4]))
    lines.append("  )")
    return "\n".join(lines)


def emit_header():
    lines = [f'  (footprint "diy:PinHeader_1x08_P2.54mm_Vertical" (layer "F.Cu")',
             f'    (uuid "{u()}")',
             f'    (at {f(HDR_X)} {f(BUS_Y0)})',
             '    (descr "1x8 vertical pin header: 1-4=ROW1-4(GP1-4), 5-8=COL1-4(GP5-8)")',
             '    (attr through_hole)',
             prop("Reference", "J1", -3.2, 0, "F.SilkS", hide=False),
             prop("Value", "RP2040 GPIO", 0, 20.5, "F.Fab")]
    for x1, y1, x2, y2 in ((-1.9, -1.27, 1.9, -1.27), (1.9, -1.27, 1.9, 19.05),
                           (1.9, 19.05, -1.9, 19.05), (-1.9, 19.05, -1.9, -1.27)):
        lines.append(fp_line(x1, y1, x2, y2))
    lines.append(fp_line(-1.9, 0.63, -0.63, -1.27))  # pin1 斜角标记
    for i, net in enumerate(BUS_NET):
        shape = "rect" if i == 0 else "circle"
        lines.append(fp_pad(str(i + 1), 0, i * PIN_P, 1.8, 1.0, net, shape))
    lines.append("  )")
    return "\n".join(lines)


def emit_hole(idx, x, y):
    return "\n".join([
        '  (footprint "diy:MountingHole_M3" (layer "F.Cu")',
        f'    (uuid "{u()}")',
        f'    (at {f(x)} {f(y)})',
        '    (attr through_hole)',
        prop("Reference", f"H{idx}", 0, -3, "F.SilkS"),
        prop("Value", "MountingHole_M3", 0, 3, "F.Fab"),
        f'    (pad "" np_thru_hole circle (at 0 0) (size 3.2 3.2) (drill 3.2) '
        f'(layers "*.Cu" "*.Mask") (uuid "{u()}"))',
        "  )"])


for i in range(16):
    x = X0 + P * i
    parts.append(emit_switch(i, x, YK))
    parts.append(emit_diode(i, x + 4, YK + DIODE_DY))
parts.append(emit_header())
for i, (hx, hy) in enumerate(HOLES):
    parts.append(emit_hole(i + 1, hx, hy))

for x1, y1, x2, y2, layer, net in segs:
    parts.append(f'  (segment (start {f(x1)} {f(y1)}) (end {f(x2)} {f(y2)}) '
                 f'(width {TRACK}) (layer "{layer}") (net {NET_ID[net]}) (uuid "{u()}"))')

for x, y, net in vias:
    parts.append(f'  (via (at {f(x)} {f(y)}) (size {VIA_D}) (drill {VIA_DRILL}) '
                 f'(layers "F.Cu" "B.Cu") (net {NET_ID[net]}) (uuid "{u()}"))')

ex1, ey1, ex2, ey2 = EDGE
for x1, y1, x2, y2 in ((ex1, ey1, ex2, ey1), (ex2, ey1, ex2, ey2),
                       (ex2, ey2, ex1, ey2), (ex1, ey2, ex1, ey1)):
    parts.append(f'  (gr_line (start {f(x1)} {f(y1)}) (end {f(x2)} {f(y2)}) '
                 f'(stroke (width 0.05) (type solid)) (layer "Edge.Cuts") (uuid "{u()}"))')

for content, x, y, size in gr_texts:
    # KiCad gr_text 的 justify 只认 left/right，不收 center；
    # 用默认左对齐 + 按字宽预估左移来实现视觉居中
    xa = x - 0.325 * size * len(content)
    parts.append(f'  (gr_text "{content}" (at {f(xa)} {f(y)} 0) (layer "F.SilkS") (uuid "{u()}") '
                 f'(effects (font (size {f(size)} {f(size)}) (thickness {f(size * 0.18)}))))')

layers = "\n".join(f"    {line}" for line in [
    '(0 "F.Cu" signal)', '(31 "B.Cu" signal)',
    '(32 "B.Adhes" user "B.Adhesive")', '(33 "F.Adhes" user "F.Adhesive")',
    '(34 "B.Paste" user)', '(35 "F.Paste" user)',
    '(36 "B.SilkS" user "B.Silkscreen")', '(37 "F.SilkS" user "F.Silkscreen")',
    '(38 "B.Mask" user)', '(39 "F.Mask" user)',
    '(40 "Dwgs.User" user "User.Drawings")', '(41 "Cmts.User" user "User.Comments")',
    '(42 "Eco1.User" user "User.Eco1")', '(43 "Eco2.User" user "User.Eco2")',
    '(44 "Edge.Cuts" user)', '(45 "Margin" user)',
    '(46 "B.CrtYd" user "B.Courtyard")', '(47 "F.CrtYd" user "F.Courtyard")',
    '(48 "B.Fab" user)', '(49 "F.Fab" user)'])

net_decls = "\n".join(f'  (net {NET_ID[n]} "{n}")' for n in NETS)

pcb = f'''(kicad_pcb (version 20221018) (generator "pcbnew") (generator_version "7.0")
  (general (thickness 1.6))
  (paper "A3")
  (layers
{layers}
  )
  (title_block
    (title "16-key Piano MIDI Keyboard PCB (4x4 matrix, COL2ROW)")
    (date "2026-10-21")
    (rev "2.0")
    (comment 1 "MX switches, 19.05mm pitch, single row. Diode per key, cathode to ROW.")
    (comment 2 "J1 pin1-4=ROW1-4(GP1-4), pin5-8=COL1-4(GP5-8)")
  )
  (setup
    (pad_to_mask_clearance 0)
  )
  (net 0 "")
{net_decls}
{chr(10).join(parts)}
)
'''

# 括号配平自检
depth = 0
for ch in pcb:
    depth += (ch == "(") - (ch == ")")
    assert depth >= 0, "paren underflow"
assert depth == 0, "unbalanced parens"

open(f"{PROJ}.kicad_pcb", "w").write(pcb)
# KiCad 8+ 网络类定义从 .kicad_pcb 移入工程文件的 net_settings
open(f"{PROJ}.kicad_pro", "w").write(json.dumps(
    {"meta": {"filename": f"{PROJ}.kicad_pro", "version": 1},
     "net_settings": {
         "classes": [{
             "name": "Default",
             "clearance": 0.2,
             "track_width": TRACK,
             "via_diameter": VIA_D,
             "via_drill": VIA_DRILL,
             "microvia_diameter": 0.5,
             "microvia_drill": 0.1,
             "diff_pair_width": 0.2,
             "diff_pair_gap": 0.25,
         }],
         "meta": {"version": 3},
     }}, indent=2))
print(f"saved {PROJ}.kicad_pcb / .kicad_pro  "
      f"({len(segs)} segments, {len(vias)} vias, {len(NETS)} nets)")

# ---------- 预览图 ----------
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams["font.family"] = ["Noto Sans CJK SC", "Noto Serif CJK SC", "sans-serif"]
FCU, BCU, PAD_C, SILK = "#c0392b", "#2471a3", "#b7950b", "#555555"

fig, ax = plt.subplots(figsize=(16, 3.9), dpi=150)
ax.set_xlim(0, 320)
ax.set_ylim(70, -4)  # y 向下，与 PCB 编辑器顶视图一致
ax.set_aspect("equal")
ax.axis("off")

ax.add_patch(plt.Rectangle((ex1, ey1), ex2 - ex1, ey2 - ey1,
                           fill=False, edgecolor="black", lw=1.6))
for hx, hy in HOLES:
    ax.add_patch(plt.Circle((hx, hy), 1.6, fill=False, edgecolor="black", lw=1.0))

for x1, y1, x2, y2, layer, net in segs:
    ax.plot([x1, x2], [y1, y2], color=FCU if layer == "F.Cu" else BCU,
            lw=3.2, solid_capstyle="round",
            alpha=0.85 if layer == "F.Cu" else 0.7, zorder=2)

for x, y, net in vias:
    ax.add_patch(plt.Circle((x, y), VIA_D / 2, color="#777777", zorder=3))
    ax.add_patch(plt.Circle((x, y), VIA_DRILL / 2, color="white", zorder=4))

for x, y, d in npths:
    ax.add_patch(plt.Circle((x, y), d / 2, color="white", ec="#999999", lw=0.7, zorder=3))

for x, y, w, h in pads:
    ax.add_patch(plt.Rectangle((x - w / 2, y - h / 2), w, h, color=PAD_C, zorder=3))
    ax.add_patch(plt.Circle((x, y), 0.55, color="white", zorder=4))

for cx, cy in switches:  # MX 轴丝印外框 14x14
    ax.add_patch(plt.Rectangle((cx - 7, cy - 7), 14, 14, fill=False,
                               edgecolor=SILK, lw=0.9, zorder=5))

for cx, cy in diodes:  # 二极管本体 + 阴极色环（左端）
    ax.add_patch(plt.Rectangle((cx - 2, cy - 0.9), 4, 1.8, color="#f5b7b1",
                               ec=SILK, lw=0.8, zorder=5))
    ax.plot([cx - 1.3, cx - 1.3], [cy - 0.9, cy + 0.9], color=SILK, lw=2.2, zorder=6)

# 排针胶壳（竖放）
ax.add_patch(plt.Rectangle((HDR_X - 1.9, BUS_Y0 - 1.27), 3.8, 7 * PIN_P + 2.54,
                           fill=False, edgecolor=SILK, lw=0.9, zorder=5))

for content, x, y, size in gr_texts:
    ax.text(x, y, content, ha="center", va="center",
            fontsize=size * 3.4, color=SILK, zorder=6)

ax.text(160, -2.5, "16-key piano layout, 4x4 matrix electrically "
        "(red = F.Cu top, blue = B.Cu bottom, gold = pads, gray dots = vias)",
        ha="center", fontsize=10, fontweight="bold")
ax.text(2, 71, "Each key: ROW -- MX switch -- 1N4148 (band to ROW) -- COL;  "
        "K0..K15 = notes 60..75 left to right;  key i = ROW(i//4) + COL(i%4);  "
        "board 316x66mm", ha="left", fontsize=8.5, color="#333333")

fig.savefig(f"{PROJ}_pcb_preview.png", bbox_inches="tight", facecolor="white")
print(f"saved {PROJ}_pcb_preview.png")
