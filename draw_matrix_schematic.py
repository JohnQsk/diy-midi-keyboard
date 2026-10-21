"""生成 12 键 3×4 矩阵原理图 matrix_12key_schematic.png / .svg。"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Arc

plt.rcParams["font.family"] = ["Noto Sans CJK SC", "sans-serif"]
plt.rcParams["svg.fonttype"] = "path"  # SVG 内嵌字形，跨机器不乱码

ROW_COLOR = "#c0392b"
COL_COLOR = "#2471a3"
COMP_COLOR = "#222222"

COLS_X = [300, 480, 660, 840]          # GP4 GP5 GP6 GP7
ROWS_Y = [150, 290, 430]               # GP1 GP2 GP3
COL_LABELS = ["GP4", "GP5", "GP6", "GP7"]
ROW_LABELS = ["GP1", "GP2", "GP3"]

fig, ax = plt.subplots(figsize=(9.8, 6.0), dpi=150)
ax.set_xlim(0, 980)
ax.set_ylim(595, 0)  # y 轴向下，方便按像素布局
ax.axis("off")

ax.text(490, 28, "12 键 3×4 矩阵接线原理图（COL2ROW）",
        ha="center", va="center", fontsize=15, fontweight="bold")

# 列线（竖，蓝）
for cx in COLS_X:
    ax.plot([cx, cx], [70, 470], color=COL_COLOR, lw=1.8, solid_capstyle="round")
for cx, label in zip(COLS_X, COL_LABELS):
    ax.text(cx, 56, label, ha="center", va="center", fontsize=11,
            color=COL_COLOR, fontweight="bold")

# 行线（横，红）
for ry in ROWS_Y:
    ax.plot([120, 880], [ry, ry], color=ROW_COLOR, lw=1.8, solid_capstyle="round")
for ry, label in zip(ROWS_Y, ROW_LABELS):
    ax.text(110, ry, label, ha="right", va="center", fontsize=11,
            color=ROW_COLOR, fontweight="bold")

# 行列交叉处：白底盖断列线 + 红色半圆弧 = 跨线不连接
for ry in ROWS_Y:
    for cx in COLS_X:
        ax.add_patch(plt.Circle((cx, ry - 9), 5.5, color="white", zorder=3))
        ax.add_patch(Arc((cx, ry), 18, 18, theta1=180, theta2=360,
                         color=ROW_COLOR, lw=1.8, zorder=4))


def key(cx, ry, label):
    """在 (cx, ry) 交叉点画一个键：行 ●── 二极管 ── 开关 ──● 列（阴极朝行）。"""
    yb = ry - 50
    ax.plot([cx - 90, cx - 90], [ry, yb], color=COMP_COLOR, lw=1.4)   # 行引脚上拐
    ax.plot([cx - 90, cx - 74], [yb, yb], color=COMP_COLOR, lw=1.4)   # 到二极管
    # 二极管：色环端（阴极）朝左=朝行线
    ax.plot([cx - 74, cx - 74], [yb - 8, yb + 8], color=COMP_COLOR, lw=2.6)  # 阴极竖杠
    ax.add_patch(plt.Polygon([(cx - 74, yb), (cx - 58, yb - 8), (cx - 58, yb + 8)],
                             closed=True, color=COMP_COLOR))                   # 三角
    ax.plot([cx - 58, cx - 30], [yb, yb], color=COMP_COLOR, lw=1.4)   # 到开关
    # 常开开关
    ax.plot([cx - 30, cx - 11], [yb, yb - 13], color=COMP_COLOR, lw=1.6)
    ax.add_patch(plt.Circle((cx - 30, yb), 2.2, color=COMP_COLOR))
    ax.add_patch(plt.Circle((cx - 6, yb), 2.2, color=COMP_COLOR))
    ax.plot([cx - 6, cx], [yb, yb], color=COMP_COLOR, lw=1.4)         # 到列线
    # 连接点
    ax.add_patch(plt.Circle((cx - 90, ry), 3.4, color=ROW_COLOR, zorder=5))
    ax.add_patch(plt.Circle((cx, yb), 3.4, color=COL_COLOR, zorder=5))
    ax.text(cx - 45, yb - 16, label, ha="center", va="center", fontsize=9.5,
            color=COMP_COLOR)


for ri, ry in enumerate(ROWS_Y):
    for ci, cx in enumerate(COLS_X):
        key(cx, ry, f"K{ri * 4 + ci}")

# 图例：二极管方向
lx, ly = 150, 508
ax.plot([lx - 45, lx - 16], [ly, ly], color=COMP_COLOR, lw=1.4)
ax.plot([lx - 16, lx - 16], [ly - 8, ly + 8], color=COMP_COLOR, lw=2.6)
ax.add_patch(plt.Polygon([(lx - 16, ly), (lx - 2, ly - 8), (lx - 2, ly + 8)],
                         closed=True, color=COMP_COLOR))
ax.plot([lx - 2, lx + 25], [ly, ly], color=COMP_COLOR, lw=1.4)
ax.text(lx + 33, ly, "= 1N4148，色环端（阴极）朝行线，12 个方向必须一致",
        ha="left", va="center", fontsize=10)

# 说明
notes = [
    "行 GP1~GP3：输出，扫描时轮流拉低，空闲置高阻（高阻 + 内部上拉，无需任何外部电阻）",
    "列 GP4~GP7：输入 + 内部上拉；某键按下时，被拉低的行把对应列拉低 → 检出",
    "二极管防鬼键（全键无冲）；行线与列线交叉处有圆弧 = 跨线，不连接",
    "K0..K11 → MIDI 音符 60..71（C4..B4）；固件 matrix_12key.py；GPIO 均接 RP2040 / RP2040-Zero",
]
for i, t in enumerate(notes):
    ax.text(120, 534 + i * 18, "· " + t, ha="left", va="center", fontsize=9.5,
            color="#333333")

fig.savefig("matrix_12key_schematic.png", bbox_inches="tight", facecolor="white")
fig.savefig("matrix_12key_schematic.svg", bbox_inches="tight", facecolor="white")
print("saved matrix_12key_schematic.png / .svg")
