# AGENTS.md — DIY 机械轴 MIDI 键盘

> 本文件面向 AI 编码代理。项目所有文档与代码注释均以中文为主，请用中文与用户交流。

## 项目概述

用机械键盘轴（MX 轴）自制 USB MIDI 键盘的 DIY 硬件项目：机械轴 → 按键扫描 → RP2040 主控 → USB MIDI（Note On/Off）→ 电脑端合成器发声。这是一个**硬件 + 固件项目**，没有传统的软件构建/打包/部署流程，代码量很小，大量内容在 Markdown 文档中。

**当前已定决策（详见 `research.md` 与 `diy.mechanical.midi.keyboard.md`）：**

- 25 键单排半音阶布局（键心距 19.05mm）；12 键原型先行
- 主控 RP2040-Zero（Waveshare 版），固件**裸 CircuitPython + `adafruit_midi` 库**，不用 QMK/KMK
- 力度第一版固定值（80 或 100）+ 旋钮；PCB 预留双触点焊盘供二期升级
- 矩阵 + 每键 1N4148 二极管直连（不用 74HC148/138/165 等省线芯片，见 `diy.mechanical.midi.keyboard.md` 的讨论）
- 路线：免焊面包板原型验证链路 → 画正式 PCB（嘉立创免费打样，10×10cm 以内）
- 键位映射：K0..K11 → MIDI 音符 60..71（C4..B4），消抖 5ms

## 目录结构与模块划分

没有包结构，全部文件平铺在仓库根目录。按用途分三组：

**CircuitPython 固件**（拷到 CIRCUITPY 盘改名 `code.py` 运行，本机只是编辑场所）：

- `matrix_12key.py` — 12 键 3×4 矩阵版固件。行 GP1~GP3 输出轮流拉低，列 GP4~GP7 输入+内部上拉；二极管 COL2ROW（阴极朝行线）。
- `matrix_16key.py` — 16 键 4×4 矩阵版固件，配 `midi_matrix_4x4` PCB（**当前首选**）。行 GP1~GP4、列 GP5~GP8，J1 pin k 直连 GPk；K0..K15 → 音符 60..75。
- `hc165_12key.py` — 12 键 74HC165 移位寄存器版固件（备选，无矩阵无二极管，可扩 64 键，GPIO 恒为 3 个：GP9/GP10/GP11）。
- 三版固件共用同一套消抖/发 MIDI 的循环结构，都在串口打印 `note on <n>` / `note off <n>`（供 `keydash.py` 解析）。

**电脑端工具（CPython 3，在开发机上运行）：**

- `keydash.py` — 串口仪表盘。读 `/dev/ttyACM0`（可传参换端口）解析固件串口输出，ANSI 实时渲染按键状态/时长/次数。依赖 `pyserial`（无 requirements.txt，需 `pip install pyserial`）。
- `draw_matrix_schematic.py` — 用 matplotlib 生成 12 键矩阵接线示意图 `matrix_12key_schematic.png` / `.svg`。需 Noto Sans CJK SC 字体显示中文。
- `gen_kicad_schematic.py` — 生成原理图 `midi_matrix.kicad_sch` / `midi_matrix.kicad_pro`（从系统符号库 `/usr/share/kicad/symbols/` 提取并内嵌符号，无需库表配置）。输出仍是 KiCad 7 文件格式（version 20230121），KiCad 10 可直接打开。
- `gen_kicad_pcb_4x4.py` — 生成 16 键单排钢琴布局 PCB `midi_matrix_4x4.kicad_pcb` / `.kicad_pro`（封装内嵌，无需库表；网络类定义按 KiCad 8+ 规范写在 `.kicad_pro` 的 `net_settings` 里，不再放 `.kicad_pcb`）+ 顶视图预览 `midi_matrix_4x4_pcb_preview.png`。MX 轴 19.05mm 键距单排，电气上仍是 4×4 矩阵（键 i = ROW(i//4) + COL(i%4)），二极管横放在键上方空隙，8 条总线在键下方 B.Cu 横走直连左侧 1×8 竖排针，板框 316×66mm。

- `draw_module_1x4_concept.py` — 生成方案 B（同款 1×4 键模块级联）概念示意图 `module_1x4_concept.png` / `.svg`。
- `draw_module_1x4_schematic.py` — 生成方案 B 单模块接线原理图 `module_1x4_schematic.png` / `.svg`（8 线 J1→J2 直通，SJ1-4 焊桥选行，4 键挂 ROW_sel × COL1-4）。
- `draw_module_wiring.py` — 生成方案 B 整机组装连线框图 `module_wiring.png` / `.svg`（RP2040-Zero + 4 块同款模块级联：每块只焊一个 SJ 选行，J2→J1 对插，GP1-4→pin1-4、GP5-8→pin5-8）。
- `gen_easyeda_module_1x4.py` — 用嘉立创 EDA 专业版 CLI（`lceda-pro invoke` + eda API）生成方案 B 模块原理图工程 `midi_module_1x4.eprj3/`（EPRJ3 文件夹格式）并导出 `module_1x4_easyeda.png`。器件用真实立创库件（MX 轴 CPG151101S11、1N4148、8P 排针/排母；SJ 焊桥用 1×2P 排针符号代替）。
- `gen_easyeda_module_1x4_pcb.py` — 模块 PCB 生成器（在原理图之后跑）：92.5×40mm 双层板（3640×1575mil），J1/J2 竖放在左右两侧板边中央（1×8P 旋 90°，焊 90° 弯针公头，8P F-F 杜邦线侧插级联）；两侧各留 320mil 边距，代价是模块接缝处键距约 35.3mm（不再连续）。SJ1-4 在板下部中央，8 条总线底层横走、两侧顶层 90° 扇出下接，ROW_SEL 全顶层走线，DRC 0 违规，导出 `module_1x4_easyeda_pcb.png`。幂等。注意：CPG151101S11 库封装是热插拔轴座（含 FILL 铜皮和槽圆），生成器会复制改造成纯 5 孔焊接封装，别直接用库原件；DRC 对过孔按孔+盘（Ø32mil 有效直径）算间距，过孔用 12/20mil。

**嘉立创 EDA 工程（方案 B 模块）：**

- `midi_module_1x4.eprj3/` — EPRJ3 文件夹格式工程（文件夹 + JSON 行记录，git 友好），编辑器打开时与磁盘双向同步
- lceda-pro 使用要点：本地 EPRJ3 必须"手写最小 `.eprj3` 索引 + `lceda-pro open --path <dir> --headless true`（在线模式下 `createProject` 会落到云端、忽略 EPRJ3 参数）；常驻无头会话不要 `stop`/`session close`；坐标系 y 轴向上；改图优先改 `gen_easyeda_module_1x4.py` 重跑（幂等），别手改工程文件

**KiCad 工程（项目名 `midi_matrix`）：**

- `midi_matrix.kicad_sch` / `.kicad_pro` / `.kicad_prl` — 12 键 3×4 矩阵原理图及工程文件
- `midi_matrix_4x4.kicad_pcb` / `.kicad_pro` — 16 键单排钢琴布局 PCB（电气 4×4 矩阵；独立工程，无对应原理图，封装内嵌）
- `midi_matrix.pdf`、`midi_matrix_preview.png` — 原理图导出件
- `midi_matrix-backups/` — KiCad 自动备份 zip，勿手改

**文档（先读这些再动代码）：**

- `README.md` — 16 键 PCB（`midi_matrix_4x4`）到手后的组装/焊接/接线/验证指南（J1→GP 接线表、二极管方向、排障）
- `research.md` — 调研报告：已定产品决策、固件选型、开源参考项目、力度方案对比、BOM 实价、嘉立创打样规则、Linux 链路坑、原型购物清单
- `diy.mechanical.midi.keyboard.md` — 方案讨论：整体架构、省线芯片否决理由、两版 12 键原型设计细节、原型进展日志
- `secondhand.buying.guide.md` — 二手成品 MIDI 键盘选购指南（与 DIY 对照）

## 构建与验证命令

无构建系统、无包管理清单、无测试套件。"验证" = 生成物能产出 + 硬件链路能跑通：

```bash
# 重新生成 KiCad 原理图（本机为 KiCad 10，经 ppa:kicad/kicad-10.0-releases 安装，符号库在 /usr/share/kicad/symbols/）
python3 gen_kicad_schematic.py

# 验证生成的原理图可渲染（需 kicad-cli）
kicad-cli sch export pdf -o midi_matrix.pdf midi_matrix.kicad_sch

# 重新生成 matplotlib 接线示意图
python3 draw_matrix_schematic.py

# 运行串口仪表盘（开发机需 pip install pyserial）
python3 keydash.py [/dev/ttyACM0]
```

**固件部署：** 把 `matrix_12key.py`（或 `hc165_12key.py`）复制到 CIRCUITPY 卷并改名 `code.py`。运行环境是 CircuitPython 9.x（waveshare_rp2040_zero 版 UF2）+ `adafruit_midi` 库，开发机上无法执行/导入这些脚本（`board`、`usb_midi` 等模块不存在）——不要在本机尝试跑它们或用 lint 工具的"模块未找到"报错当 bug。

**硬件端验收流程**（Linux，免驱）：

1. `aconnect -l` 认出 USB MIDI 设备
2. `aseqdump -p <端口>` 抓到干净的 Note On/Off 配对，无连发无丢失
3. QSynth/FluidSynth **加载 SoundFont**（如 FluidR3_GM.sf2，最常见坑是忘加载导致无声）后 `aconnect <键盘> <fluidsynth>` 发声
4. MuseScore 能录入

## 代码风格约定

- 语言：固件与生成器脚本的 docstring/注释用**中文**（`keydash.py` 是英文 docstring 的例外）；硬件原理图注释用英文
- 固件常量集中在文件头部（`ROW_PINS`、`BASE_NOTE`、`VELOCITY`、`DEBOUNCE_S` 等），改参数只动这里
- 消抖逻辑两版固件保持一致：raw 变化记录时间戳，稳定超过 `DEBOUNCE_S`（5ms）才提交状态并发 MIDI 消息；主循环 `time.sleep(0.001)`
- 固件串口输出格式必须保持 `note on <n>` / `note off <n>`，`keydash.py` 靠子串匹配解析
- 生成器脚本（`gen_kicad_schematic.py`、`draw_matrix_schematic.py`）自包含、无第三方配置依赖，顶部 docstring 写明运行与验证方法

## 测试

无自动化测试。验证手段按层：

- 生成器脚本：跑一遍看输出文件是否生成 + 用 `kicad-cli sch export pdf` 渲染确认
- 固件：串口看 `note on/off` 输出是否干净（配 `keydash.py` 或 `aseqdump`）；零成本预验证 = 杜邦线短接 GPIO 与 GND 模拟按键
- 改固件后要在真硬件上验证和弦无鬼键、无连发无丢失

## 安全与注意事项

- 不要手改 `midi_matrix-backups/` 下的 KiCad 自动备份
- 改 KiCad 原理图优先改 `gen_kicad_schematic.py` 再重新生成，而不是直接编辑 `.kicad_sch`（两者要保持同步）
- 固件脚本里 `adafruit_midi`、`board`、`usb_midi` 等是 CircuitPython 板载库，不要往仓库加 pip 依赖
- 硬件方向性约束写死在多处文档和注释里：二极管 COL2ROW（色环端/阴极朝行线）、12 个必须同向——改动时全文检索保持一致

## 当前进度（2026-10-26，晚）

**全链路已打通并实际发声**：1×4 模块板（EasyEDA 方案 B）焊了 3 个键（K1/K2/K3，SJ3 选 ROW3），接 RP2040-Zero + `matrix_16key.py` 固件，经 FluidSynth（`/usr/share/sounds/sf2/default-GM.sf2`）+ `aconnect 20:0 128:0` 出声。K2/K3（音符 70/71）工作正常，`aseqdump` 抓到干净 Note On/Off 配对，无连发无丢失。待办：D1/D2 二极管焊反导致 K1（音符 69）无反应，需翻转重焊（与 D3/D4 同向）；其余键位和二极管后续补焊。

经验：FluidSynth 后台常驻不能用 `-i`（会静默退出），正确做法是保留交互 shell 并保持 stdin 打开：`sleep infinity | fluidsynth -a pulseaudio -m alsa_seq <sf2>`；开发机串口 `/dev/ttyACM0` 需用户在 `dialout` 组（尚未配置，`keydash.py` 暂不可用，`aseqdump` 走 ALSA 不受影响）。16 键长条 PCB（`midi_matrix_4x4`）也已打样到手，组装接线见 `README.md`。
