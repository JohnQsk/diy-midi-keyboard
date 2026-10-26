# DIY 机械轴 MIDI 键盘 — PCB 组装与接线

适用板子：`midi_matrix_4x4.kicad_pcb`（16 键单排钢琴布局，316×66mm 双层板，
电气上 4×4 矩阵）。键位从左到右 K0..K15 = MIDI 音符 60..75（C4..D#5）。

## 物料清单

| 物料 | 数量 | 说明 |
|---|---|---|
| Cherry MX 兼容机械轴 | 16 | 5 脚 PCB 安装轴（3 脚板载轴也能焊，但没有定位柱固定） |
| 1N4148 二极管（DO-35） | 16 | 方向必须全部一致，见下文 |
| 1×8 排针（2.54mm） | 1 | 焊在 J1 |
| RP2040-Zero（Waveshare） | 1 | 刷 CircuitPython 9.x |
| 杜邦线（母对母） | 8 | 连接 J1 与 RP2040-Zero |

## 焊接

按从矮到高的顺序焊：**二极管 → 排针 → 轴**。

1. **二极管 D1..D16（最关键，别焊反）**
   每个键上方有一只 1N4148，横放。丝印上本体左侧有一条粗线标记——那是
   **阴极（色环端）**。二极管玻璃体上的黑色/彩色环必须朝这个标记（左侧焊盘，
   即靠近轴体 pin1 的那一端）。16 只全部同向（COL2ROW，阴极朝行线）。
   焊反一只，对应键就完全没反应（或整行/列行为异常）。

2. **排针 J1**
   板子左边缘的 1×8 竖排针。从正面插入，背面焊接。
   pin1 在丝印斜角/方焊盘处，pin1..8 旁边有数字 1..8 丝印。

3. **MX 轴 SW1..SW16**
   对准 5 个孔（2 个电气脚 + 中心柱 + 2 个定位柱）按入，焊两个电气脚即可。
   注意丝印键号 K0 在最左、K15 在最右。

## 接线（J1 → RP2040-Zero）

8 根杜邦线一一对应，**不需要接 GND**（矩阵全是 GPIO 直连，主控由 USB 供电）：

| J1 pin | 信号 | RP2040-Zero |
|---|---|---|
| 1 | ROW1 | GP1 |
| 2 | ROW2 | GP2 |
| 3 | ROW3 | GP3 |
| 4 | ROW4 | GP4 |
| 5 | COL1 | GP5 |
| 6 | COL2 | GP6 |
| 7 | COL3 | GP7 |
| 8 | COL4 | GP8 |

即 J1 pin k → GPk，直插到底即可。

## 固件

1. RP2040-Zero 刷 CircuitPython 9.x（waveshare_rp2040_zero 版 UF2），
   并把 `adafruit_midi` 库拷到 CIRCUITPY 盘的 `lib/`。
2. 把本仓库的 `matrix_16key.py` 拷到 CIRCUITPY 盘，**改名 `code.py`**。
3. 上电后电脑应直接识别为 USB MIDI 设备（Linux 免驱）。

固件行为：行线轮流拉低扫描、列线内部上拉，5ms 消抖，固定力度 80，
串口（USB CDC）打印 `note on <n>` / `note off <n>`。

## 验证

```bash
aconnect -l                  # 应看到 USB MIDI 设备
aseqdump -p <端口>           # 按键应出现干净的 Note On/Off 配对
python3 keydash.py           # 或用串口仪表盘实时看按键状态（需 pip install pyserial）
```

发声：QSynth/FluidSynth 加载 SoundFont（如 FluidR3_GM.sf2，**忘加载是最常见的"没声音"原因**），
然后 `aconnect <键盘端口> <fluidsynth端口>`。

## 排障

- 某个键没反应 → 先查该键的二极管方向，再查轴体两个焊点。
- 一整行（K0-3 / K4-7 / K8-11 / K12-15 之一）没反应 → 查对应 ROW 的杜邦线/GP 口。
- 一列（K0,K4,K8,K12 这种间隔 4 的）没反应 → 查对应 COL 的杜邦线/GP 口。
- 按键串扰/鬼键 → 基本就是某只二极管焊反或漏焊。
