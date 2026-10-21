"""生成方案 B 单模块（1x4 键）接线原理图 module_1x4_schematic.png / .svg。

8 根线（ROW1-4 + COL1-4）从 J1 直通到 J2 级联下一块；
本板的 4 个键挂在 ROW_sel（经 SJ1-4 焊桥四选一）与 COL1-4 之间。
跨线圆弧 = 不连接。运行：python3 draw_module_1x4_schematic.py
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Arc

plt.rcParams["font.family"] = ["Noto Sans CJK SC", "Noto Serif CJK SC", "sans-serif"]
plt.rcParams["svg.fonttype"] = "path"

ROW_COLOR = "#c0392b"
COL_COLOR = "#2471a3"
COMP_COLOR = "#222222"

COLS_X = [500, 660, 820, 980]          # COL1..COL4 竖线
ROW_YS = [130, 165, 200, 235]          # ROW1..ROW4 直通线
RSEL_Y = 345                           # 本板行线（经 SJ 选择）
KEY_BR_Y = 295                         # 键分支高度
COL_BUS_Y = [450, 466, 482, 498]       # COL 底部直通横线
SJ_X = [270, 305, 340, 375]            # SJ1..SJ4
SJ_PAD1, SJ_PAD2 = 250, 272            # 焊桥上下焊盘 y
J1_X, J2_X = 150, 1010                 # 连接器出线 x

fig, ax = plt.subplots(figsize=(11.5, 7.0), dpi=150)
ax.set_xlim(0, 1150)
ax.set_ylim(700, 0)  # y 轴向下
ax.axis("off")

ax.text(575, 30, "1x4 module schematic (4 identical boards = 16-key piano row)",
        ha="center", va="center", fontsize=15, fontweight="bold")


def hop(cx, cy, color):
    """跨线不连接：白底盖断 + 半圆弧。"""
    ax.add_patch(plt.Circle((cx, cy - 9), 5.5, color="white", zorder=3))
    ax.add_patch(Arc((cx, cy), 18, 18, theta1=180, theta2=360,
                     color=color, lw=1.8, zorder=4))


def hline(x1, x2, y, color):
    ax.plot([x1, x2], [y, y], color=color, lw=1.8, solid_capstyle="round")


def vline(x, y1, y2, color):
    ax.plot([x, x], [y1, y2], color=color, lw=1.8, solid_capstyle="round")


# ---------- COL 竖线 + 底部直通横线（竖线压横线处由横线跨弧） ----------
for j, cx in enumerate(COLS_X):
    vline(cx, 100, COL_BUS_Y[j], COL_COLOR)
    hline(J1_X, J2_X, COL_BUS_Y[j], COL_COLOR)
    ax.text(cx, 92, f"COL{j + 1}", ha="center", va="center", fontsize=9,
            color=COL_COLOR, fontweight="bold")
# COL 横线之间的交叉（COL1 横线跨 COL2-4 竖线，依此类推）
for j in range(3):
    for k in range(j + 1, 4):
        hop(COLS_X[k], COL_BUS_Y[j], COL_COLOR)

# ---------- ROW1-4 直通横线（跨 COL 竖线） ----------
for ri, ry in enumerate(ROW_YS):
    hline(J1_X, J2_X, ry, ROW_COLOR)
    for cx in COLS_X:
        hop(cx, ry, ROW_COLOR)

# ---------- SJ1-4 焊桥：ROWj 竖直短桩 → 上焊盘 ‖ 下焊盘 → ROW_sel ----------
# 短桩跨下方 ROW 线处画弧
for j, sx in enumerate(SJ_X):
    vline(sx, ROW_YS[j], SJ_PAD1 - 4, ROW_COLOR)
    for k in range(j + 1, 4):
        hop(sx, ROW_YS[k], ROW_COLOR)
    for py in (SJ_PAD1, SJ_PAD2):  # 焊盘
        ax.add_patch(plt.Rectangle((sx - 6, py - 4), 12, 8, fill=False,
                                   ec=ROW_COLOR, lw=1.3, zorder=4))
    ax.text(sx + 12, (SJ_PAD1 + SJ_PAD2) / 2, f"SJ{j + 1}", ha="left",
            va="center", fontsize=7.5, color=ROW_COLOR)
    vline(sx, SJ_PAD2 + 4, RSEL_Y, ROW_COLOR)
    ax.add_patch(plt.Circle((sx, RSEL_Y), 3.0, color=ROW_COLOR, zorder=5))
# SJ1 示例已桥接（焊锡 blob）
ax.plot([SJ_X[0], SJ_X[0]], [SJ_PAD1 + 4, SJ_PAD2 - 4], color=ROW_COLOR, lw=5.0,
        solid_capstyle="round", zorder=5)

# ---------- ROW_sel 横线（跨 COL 竖线） ----------
hline(SJ_X[0], 990, RSEL_Y, ROW_COLOR)
for cx in COLS_X:
    hop(cx, RSEL_Y, ROW_COLOR)
ax.text(988, RSEL_Y + 17, "ROW_sel", ha="right", va="center", fontsize=10,
        color=ROW_COLOR, fontweight="bold")


def key(cx, label):
    """键分支：ROW_sel ●── 二极管(色环朝行) ── 开关 ──● COL 竖线。"""
    yb = KEY_BR_Y
    vline(cx - 90, yb, RSEL_Y, COMP_COLOR)                    # 行引脚下接
    ax.add_patch(plt.Circle((cx - 90, RSEL_Y), 3.4, color=ROW_COLOR, zorder=5))
    ax.plot([cx - 90, cx - 74], [yb, yb], color=COMP_COLOR, lw=1.4)
    ax.plot([cx - 74, cx - 74], [yb - 8, yb + 8], color=COMP_COLOR, lw=2.6)  # 阴极竖杠
    ax.add_patch(plt.Polygon([(cx - 74, yb), (cx - 58, yb - 8), (cx - 58, yb + 8)],
                             closed=True, color=COMP_COLOR))
    ax.plot([cx - 58, cx - 30], [yb, yb], color=COMP_COLOR, lw=1.4)
    ax.plot([cx - 30, cx - 11], [yb, yb - 13], color=COMP_COLOR, lw=1.6)     # 常开开关
    ax.add_patch(plt.Circle((cx - 30, yb), 2.2, color=COMP_COLOR))
    ax.add_patch(plt.Circle((cx - 6, yb), 2.2, color=COMP_COLOR))
    ax.plot([cx - 6, cx], [yb, yb], color=COMP_COLOR, lw=1.4)
    ax.add_patch(plt.Circle((cx, yb), 3.4, color=COL_COLOR, zorder=5))
    ax.text(cx - 45, yb - 16, label, ha="center", va="center", fontsize=9.5,
            color=COMP_COLOR)


for c, cx in enumerate(COLS_X):
    key(cx, f"K{c}")

# ---------- 连接器 ----------
ax.add_patch(plt.Rectangle((J1_X - 60, 110), 60, 415, fill=False,
                           ec=COMP_COLOR, lw=1.5))
ax.text(J1_X - 30, 100, "J1 (8P, F)", ha="center", va="center", fontsize=10,
        fontweight="bold")
ax.add_patch(plt.Rectangle((J2_X, 110), 60, 415, fill=False,
                           ec=COMP_COLOR, lw=1.5))
ax.text(J2_X + 30, 100, "J2 (8P, M)", ha="center", va="center", fontsize=10,
        fontweight="bold")

for i in range(8):
    py = ROW_YS[i] if i < 4 else COL_BUS_Y[i - 4]
    net = f"ROW{i + 1}" if i < 4 else f"COL{i - 3}"
    color = ROW_COLOR if i < 4 else COL_COLOR
    ax.text(J1_X - 66, py, net, ha="right", va="center", fontsize=9,
            color=color, fontweight="bold")
    ax.text(J2_X + 66, py, net, ha="left", va="center", fontsize=9,
            color=color, fontweight="bold")
    ax.text(J1_X - 8, py, str(i + 1), ha="right", va="center", fontsize=7.5,
            color="#888888")
    ax.text(J2_X + 8, py, str(i + 1), ha="left", va="center", fontsize=7.5,
            color="#888888")

# ---------- 说明 ----------
notes = [
    "All 8 nets pass straight through J1 -> J2 (daisy-chain bus to next module / RP2040).",
    "SJ1-4: solder ONE jumper to select this board's row (SJ1 shown bridged -> MOD A = ROW1).",
    "Each key: ROW_sel -- SW -- 1N4148 -- COL; diode band (cathode) faces ROW (COL2ROW), all 4 identical.",
    "Module j, position c -> MIDI note 60+(j-1)*4+(c-1); firmware unchanged: GP1-4 = ROW1-4, GP5-8 = COL1-4.",
]
for i, t in enumerate(notes):
    ax.text(90, 570 + i * 26, "· " + t, ha="left", va="center", fontsize=10,
            color="#333333")

fig.savefig("module_1x4_schematic.png", bbox_inches="tight", facecolor="white")
fig.savefig("module_1x4_schematic.svg", bbox_inches="tight", facecolor="white")
print("saved module_1x4_schematic.png / .svg")
