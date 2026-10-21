"""生成模块级联实物连线框图 module_wiring.png / .svg。

4 块相同的 1x4 模块板 + RP2040-Zero：谁插谁、每块板焊哪个 SJ、
GP 引脚对排针引脚的对应关系、组装步骤。
运行：python3 draw_module_wiring.py
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams["font.family"] = ["Noto Sans CJK SC", "Noto Serif CJK SC", "sans-serif"]
plt.rcParams["svg.fonttype"] = "path"

ROW_COLOR = "#c0392b"
COL_COLOR = "#2471a3"
COMP_COLOR = "#222222"
GRAY = "#666666"

NOTES = ["C4", "C#4", "D4", "D#4", "E4", "F4", "F#4", "G4",
         "G#4", "A4", "A#4", "B4", "C5", "C#5", "D5", "D#5"]

fig, ax = plt.subplots(figsize=(13, 6.8), dpi=150)
ax.set_xlim(0, 1300)
ax.set_ylim(680, 0)  # y 轴向下
ax.axis("off")

ax.text(650, 28, "Wiring: 4 identical 1x4 modules + RP2040-Zero = 16-key piano row",
        ha="center", va="center", fontsize=15, fontweight="bold")

CARD_Y0, CARD_Y1 = 170, 320
CARD_X = [320, 557, 794, 1031]   # 4 张模块卡左缘
CARD_W = 215

# ---------- RP2040-Zero ----------
ax.add_patch(plt.Rectangle((30, 180), 150, 150, fill=False, ec=COMP_COLOR, lw=1.8))
ax.text(105, 200, "RP2040-Zero", ha="center", va="center", fontsize=11,
        fontweight="bold")
ax.text(105, 312, "USB -> PC", ha="center", va="center", fontsize=8.5, color=GRAY)
GP_Y = [222 + i * 13 for i in range(8)]
for i, gy in enumerate(GP_Y):
    color = ROW_COLOR if i < 4 else COL_COLOR
    ax.add_patch(plt.Circle((180, gy), 2.5, color=color, zorder=5))
    ax.text(174, gy, f"GP{i + 1}", ha="right", va="center", fontsize=7.5, color=color)

# ---------- 8 根杜邦线：RP2040 -> MOD A 的 J1 ----------
J1_PIN_Y = [222 + i * 8 for i in range(8)]
for i in range(8):
    color = ROW_COLOR if i < 4 else COL_COLOR
    ax.plot([180, CARD_X[0]], [GP_Y[i], J1_PIN_Y[i]], color=color, lw=1.3, zorder=2)
ax.text(250, 305, "8 dupont wires", ha="center", va="center", fontsize=8.5,
        color=GRAY)

# ---------- 4 张模块卡 ----------
for m in range(4):
    x = CARD_X[m]
    ax.add_patch(plt.Rectangle((x, CARD_Y0), CARD_W, CARD_Y1 - CARD_Y0,
                               fill=False, ec=COMP_COLOR, lw=1.8))
    ax.text(x + 8, CARD_Y0 + 14, f"MOD {chr(65 + m)}",
            ha="left", va="center", fontsize=9.5, fontweight="bold", color=ROW_COLOR)
    ax.text(x + 8, CARD_Y0 + 27, f"solder SJ{m + 1} = ROW{m + 1}",
            ha="left", va="center", fontsize=8, color=ROW_COLOR)
    for c in range(4):
        k = m * 4 + c
        kx = x + 14 + c * 50
        ax.add_patch(plt.Rectangle((kx, 210), 40, 40, fill=False,
                                   ec=COMP_COLOR, lw=1.3))
        ax.text(kx + 20, 230, f"K{k}", ha="center", va="center", fontsize=8.5,
                color=COMP_COLOR)
        ax.text(kx + 20, 262, NOTES[k], ha="center", va="center", fontsize=7.5,
                color=GRAY)
        ax.text(kx + 20, 273, str(60 + k), ha="center", va="center", fontsize=7,
                color="#999999")
    ax.text(x + 8, CARD_Y1 - 14, "J1 (F)", ha="left", va="center", fontsize=8,
            color=GRAY)
    ax.text(x + CARD_W - 8, CARD_Y1 - 14, "J2 (M)", ha="right", va="center",
            fontsize=8, color=GRAY)

# ---------- 模块间对插 ----------
for m in range(3):
    gx = CARD_X[m] + CARD_W
    ax.add_patch(plt.Rectangle((gx + 2, 232), 8, 26, color="#dddddd",
                               ec=COMP_COLOR, lw=1.0, zorder=3))
    ax.add_patch(plt.Rectangle((gx + 12, 232), 8, 26, color="#bbbbbb",
                               ec=COMP_COLOR, lw=1.0, zorder=3))
    ax.text(gx + 11, 272, "plug", ha="center", va="center", fontsize=7.5,
            color=GRAY)

# 链尾
ax.text(CARD_X[3] + CARD_W + 10, 245, "J2 left open\n(end of chain)",
        ha="left", va="center", fontsize=8, color=GRAY)

# 总线流向说明
ax.annotate("", xy=(1246, 350), xytext=(320, 350),
            arrowprops=dict(arrowstyle="->", color=GRAY, lw=1.2))
ax.text(783, 362, "COL1-4 run through all modules; each board taps ONE row via its SJ",
        ha="center", va="center", fontsize=9.5, color=GRAY, style="italic")

# ---------- 组装/接线步骤 ----------
steps = [
    "1.  Solder all 4 boards identically: 4x MX switch, 4x 1N4148 (band faces ROW side), J1 (female) left, J2 (male) right.",
    "2.  Solder exactly ONE jumper per board:  MOD A -> SJ1,  MOD B -> SJ2,  MOD C -> SJ3,  MOD D -> SJ4.  (this is the only difference)",
    "3.  Plug the chain:  A.J2 -> B.J1,  B.J2 -> C.J1,  C.J2 -> D.J1  (left->right = notes ascending C4 -> D#5).",
    "4.  RP2040-Zero -> MOD A's J1:  GP1-4 -> pins 1-4 (ROW1-4),  GP5-8 -> pins 5-8 (COL1-4).  8 wires only, no GND/power on the bus.",
    "5.  Flash firmware as code.py:  matrix logic unchanged, ROW_PINS = GP1..GP4, COL_PINS = GP5..GP8.  Done - play.",
]
ax.text(60, 420, "Assembly / wiring steps", ha="left", va="center", fontsize=12,
        fontweight="bold")
for i, t in enumerate(steps):
    ax.text(60, 456 + i * 32, t, ha="left", va="center", fontsize=10,
            color="#333333")

ax.text(60, 640, "RP2040 can plug into either end of the chain; key j*4+c (module j, position c) = note 60+j*4+c.",
        ha="left", va="center", fontsize=9.5, color=GRAY, style="italic")

fig.savefig("module_wiring.png", bbox_inches="tight", facecolor="white")
fig.savefig("module_wiring.svg", bbox_inches="tight", facecolor="white")
print("saved module_wiring.png / .svg")
