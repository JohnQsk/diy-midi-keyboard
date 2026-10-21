"""生成方案 B（同款 1x4 键模块级联）概念示意图 module_1x4_concept.png / .svg。

上半部分：4 块相同模块级联成 16 键单排（键 = 音符 60..75 左到右）；
下半部分：单个模块内部细节（MX 轴、1N4148、两端 8P 排针、SJ1-4 焊桥选行）。
运行：python3 draw_module_1x4_concept.py
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams["font.family"] = ["Noto Sans CJK SC", "Noto Serif CJK SC", "sans-serif"]
plt.rcParams["svg.fonttype"] = "path"

ROW_COLOR = "#c0392b"
COL_COLOR = "#2471a3"
COMP_COLOR = "#222222"
BOX_COLOR = "#444444"

NOTES = ["C4", "C#4", "D4", "D#4", "E4", "F4", "F#4", "G4",
         "G#4", "A4", "A#4", "B4", "C5", "C#5", "D5", "D#5"]

fig, ax = plt.subplots(figsize=(14, 8.2), dpi=150)
ax.set_xlim(0, 1400)
ax.set_ylim(800, 0)  # y 轴向下
ax.axis("off")

ax.text(700, 26, "Option B: identical 1x4 modules daisy-chained into a 16-key piano row",
        ha="center", va="center", fontsize=15, fontweight="bold")

# ---------- 上半：级联总览 ----------
MOD_W, MOD_H = 290, 150
MOD_Y = 70
BUS_Y0, BUS_Y1 = 250, 266  # 总线条带

# 总线（画在模块后面）
ax.add_patch(plt.Rectangle((40, BUS_Y0), 1320, BUS_Y1 - BUS_Y0,
                           color="#eeeeee", ec=BOX_COLOR, lw=1.0, zorder=1))
ax.text(60, BUS_Y1 + 16, "8-wire pass-through bus: ROW1-4 + COL1-4",
        ha="left", va="center", fontsize=9, color=BOX_COLOR, zorder=4)

for m in range(4):
    mx = 40 + m * 310
    ax.add_patch(plt.Rectangle((mx, MOD_Y), MOD_W, MOD_H, fill=False,
                               ec=BOX_COLOR, lw=1.6, zorder=2))
    ax.text(mx + 10, MOD_Y + 16, f"MOD {chr(65 + m)}: bridge SJ{m + 1} = ROW{m + 1}",
            ha="left", va="center", fontsize=9, fontweight="bold", color=ROW_COLOR)
    for c in range(4):
        k = m * 4 + c
        kx = mx + 22 + c * 66
        ax.add_patch(plt.Rectangle((kx, MOD_Y + 34), 52, 52, fill=False,
                                   ec=COMP_COLOR, lw=1.4, zorder=2))
        ax.text(kx + 26, MOD_Y + 60, f"K{k}", ha="center", va="center",
                fontsize=10, color=COMP_COLOR)
        ax.text(kx + 26, MOD_Y + 100, NOTES[k], ha="center", va="center",
                fontsize=8.5, color="#666666")
        ax.text(kx + 26, MOD_Y + 114, str(60 + k), ha="center", va="center",
                fontsize=7.5, color="#999999")
    # 模块到总线的抽头
    ax.plot([mx + MOD_W / 2, mx + MOD_W / 2], [MOD_Y + MOD_H, BUS_Y0],
            color=ROW_COLOR, lw=1.6, zorder=2)
    ax.add_patch(plt.Circle((mx + MOD_W / 2, BUS_Y0), 3.5, color=ROW_COLOR, zorder=3))
    ax.text(mx + MOD_W / 2 + 8, (MOD_Y + MOD_H + BUS_Y0) / 2, f"ROW{m + 1} tap",
            ha="left", va="center", fontsize=8, color=ROW_COLOR)
    # 模块间对插连接器
    if m < 3:
        ax.add_patch(plt.Rectangle((mx + MOD_W, BUS_Y0 - 4), 20, BUS_Y1 - BUS_Y0 + 8,
                                   color="#dddddd", ec=BOX_COLOR, lw=1.0, zorder=3))

# RP2040 接在总线末端
ax.text(1330, MOD_Y + 20, "RP2040-Zero", ha="left", fontsize=10, fontweight="bold")
ax.text(1330, MOD_Y + 38, "GP1-4 = ROW1-4", ha="left", fontsize=9, color=ROW_COLOR)
ax.text(1330, MOD_Y + 52, "GP5-8 = COL1-4", ha="left", fontsize=9, color=COL_COLOR)
ax.text(1330, MOD_Y + 66, "(plug into any", ha="left", fontsize=8.5, color="#666666")
ax.text(1330, MOD_Y + 78, "module end)", ha="left", fontsize=8.5, color="#666666")

# ---------- 下半：单模块细节 ----------
ax.text(700, 316, "Module detail — all modules are the SAME board (row selected by solder jumper)",
        ha="center", va="center", fontsize=12, fontweight="bold")

# 模块框：95x40mm 按 6px/mm
DX, DY, SC = 80, 350, 6
ax.add_patch(plt.Rectangle((DX, DY), 95 * SC, 40 * SC, fill=False, ec=BOX_COLOR, lw=1.8))
ax.text(DX + 95 * SC / 2, DY + 40 * SC + 16, "board ~95 x 40 mm (JLC free: <=10x10 cm, 2-layer)",
        ha="center", va="center", fontsize=9.5, color="#666666")

# 两端 8P 排针（左母右公）
ax.add_patch(plt.Rectangle((DX + 12, DY + 30), 26, 180, color="#f0f0f0", ec=BOX_COLOR, lw=1.2))
ax.text(DX + 25, DY + 120, "J1\n8P\n(M)", ha="center", va="center", fontsize=9, color=BOX_COLOR)
ax.add_patch(plt.Rectangle((DX + 532, DY + 30), 26, 180, color="#f0f0f0", ec=BOX_COLOR, lw=1.2))
ax.text(DX + 545, DY + 120, "J2\n8P\n(M)", ha="center", va="center", fontsize=9, color=BOX_COLOR)

# COL 列线直通（蓝，横贯）
ax.plot([DX + 38, DX + 532], [DY + 154, DY + 154], color=COL_COLOR, lw=2.0)
ax.text(DX + 285, DY + 163, "COL1-4 pass straight through to next module",
        ha="center", va="top", fontsize=9, color=COL_COLOR)

# ROW 进线经 SJ 焊桥（红）
ax.plot([DX + 38, DX + 70], [DY + 186, DY + 186], color=ROW_COLOR, lw=2.0)
for j in range(4):
    sx = DX + 70 + j * 30
    ax.add_patch(plt.Rectangle((sx, DY + 180), 10, 5, fill=False, ec=ROW_COLOR, lw=1.1))
    ax.add_patch(plt.Rectangle((sx + 14, DY + 180), 10, 5, fill=False, ec=ROW_COLOR, lw=1.1))
    ax.text(sx + 12, DY + 198, f"SJ{j + 1}", ha="center", va="center", fontsize=7.5,
            color=ROW_COLOR)
ax.plot([DX + 192, DX + 214], [DY + 182, DY + 142], color=ROW_COLOR, lw=2.0)
ax.plot([DX + 214, DX + 500], [DY + 142, DY + 142], color=ROW_COLOR, lw=2.0)
ax.text(DX + 130, DY + 216, "solder ONE jumper to pick ROW1-4 (only difference between boards)",
        ha="left", va="center", fontsize=9, color=ROW_COLOR)

# 4 个 MX 轴 + 二极管
for c in range(4):
    kx = DX + 60 + c * 114
    ax.add_patch(plt.Rectangle((kx, DY + 50), 84, 84, fill=False, ec=COMP_COLOR, lw=1.4))
    ax.text(kx + 42, DY + 92, f"K{c}", ha="center", va="center", fontsize=10,
            color=COMP_COLOR)
    # 二极管在键上方，色环朝左（朝行）
    ax.add_patch(plt.Rectangle((kx + 18, DY + 28), 24, 10, color="#f5b7b1",
                               ec=COMP_COLOR, lw=0.9))
    ax.plot([kx + 24, kx + 24], [DY + 28, DY + 38], color=COMP_COLOR, lw=2.4)
ax.annotate("1N4148 per key, band faces ROW", xy=(DX + 90, DY + 33),
            xytext=(DX + 30, DY - 14), fontsize=9, color=COMP_COLOR,
            arrowprops=dict(arrowstyle="->", color=COMP_COLOR, lw=0.9))
ax.annotate("Cherry MX x4, 19.05mm pitch", xy=(DX + 444, DY + 50),
            xytext=(DX + 400, DY - 14), fontsize=9, color=COMP_COLOR,
            arrowprops=dict(arrowstyle="->", color=COMP_COLOR, lw=0.9))

# ---------- 底部要点 ----------
notes = [
    "Free-coupon math: one order = 5 identical boards.  16 keys need 4 (+1 spare);  25-key version needs 7 (28 slots).",
    "Chaining: J2 -> next module's J1 via 8P F-F dupont cable (side entry); end of chain -> RP2040 (GP1-4 = ROW1-4, GP5-8 = COL1-4).",
    "Firmware unchanged (4x4 matrix): key at module j, position c  ->  note 60 + (j-1)*4 + (c-1).",
    "Every key: ROW -- MX switch -- 1N4148 (band to ROW) -- COL  (COL2ROW, same as before).",
]
for i, t in enumerate(notes):
    ax.text(60, 640 + i * 30, "· " + t, ha="left", va="center", fontsize=10.5,
            color="#333333")

fig.savefig("module_1x4_concept.png", bbox_inches="tight", facecolor="white")
fig.savefig("module_1x4_concept.svg", bbox_inches="tight", facecolor="white")
print("saved module_1x4_concept.png / .svg")
