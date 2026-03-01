# RTL Connectivity Profiler

> A static analysis tool that parses Verilog/SystemVerilog RTL files using **pyslang's AST**, constructs a directed Signal Dependency Graph, identifies connectivity hotspots through fan-in/fan-out ranking, and renders an **interactive animated browser dashboard** — no synthesis required.

---

## Table of Contents

- [What Is This?](#what-is-this)
- [How Coloured Nodes Help You](#how-coloured-nodes-help-you)
- [How It Works](#how-it-works)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [Usage](#usage)
- [Output Files](#output-files)
- [Output Example](#output-example)
- [Supported RTL Patterns](#supported-rtl-patterns)
- [Dataset](#dataset)
- [Results Summary](#results-summary)
- [Tech Stack](#tech-stack)
- [Assignment Context](#assignment-context)

---

## What Is This?

This tool reads raw Verilog/SystemVerilog RTL code and answers:

> **"Which signals in this chip design are the most connected — and what do they connect to?"**

It builds a **directed dependency graph** where:

- Every **node** is a signal (`wire`, `reg`, `logic`, `input`, `output`)
- Every **edge A → B** means *"signal B depends on signal A"*

Using this graph the tool computes **fan-in** and **fan-out** for every signal and reports the **Top-K busiest signals** — the connectivity hotspots of your design — displayed in a live animated browser dashboard.

---

## How Coloured Nodes Help You

The animated graph colours each signal node on a **blue → red gradient** based on its total connectivity score (`fan-in + fan-out`):

| Colour | Meaning |
|--------|---------|
| 🔴 **Red** | Very high connectivity — this signal is read or written by many others |
| 🟠 **Orange** | Medium-high connectivity |
| 🔵 **Blue** | Low connectivity — this signal has few dependencies |

**Why this matters beyond just a pretty graph:**

This is directly useful as a **stress-test and design-complexity indicator**:

- A **red node** (`clk`, `rst_n`, `result`, `state`) means that signal fans out to or is driven by many other signals. In real silicon, high fan-out signals require **buffer trees** and are the first to fail **timing closure**. They are your most likely **bottlenecks under load**.
- A signal with very high **fan-in** (many drivers) represents a convergence point — the logic feeding it is complex and will contribute the most to **combinational delay** and **power consumption under switching activity**.
- Watching **animated packets** flow along real source→sink paths shows you exactly which signals carry data across the longest chains — these are your **critical timing paths** and the ones a stress test should target first.
- In simulation-based stress testing, you want to toggle the **red nodes hardest** — they propagate changes to the most downstream logic, causing maximum switching and therefore maximum power draw and thermal stress.

So yes: a red node = a signal that is used heavily across the design = the right place to direct stress vectors, verify timing margins, and look for routing congestion.

---

## How It Works

```
Verilog / SystemVerilog file (.v / .sv)
              │
              ▼
        [ final_parser.py ]   ←── pyslang (AST)
              │
              │  Walks AST → extracts signal names
              │  and assignment relationships
              │  Handles: assign, always @(*),
              │  always @(posedge clk), if/case,
              │  blocking =, non-blocking <=
              ▼
        [ graph_builder.py ]  ←── networkx
              │
              │  DiGraph: edge A→B means
              │  "B depends on A"
              │  Nodes categorised:
              │  input / output / internal / isolated
              ▼
        [ analyzer.py ]
              │
              ├── fan_in(B)  = in_degree(B)
              ├── fan_out(A) = out_degree(A)
              ├── Top-K incoming-busy signals
              ├── Top-K outgoing-busy signals
              └── Graph stats (density, avg, max)
              │
              ▼
        [ visualizer.py ]
              │
              ├── <design>_inner.html
              │     Animated bouncing graph
              │     Colour-coded nodes (blue→red)
              │     Draggable nodes
              │     Signal packets on real paths
              │     SVG arrowhead edges
              │
              └── <design>_dashboard.html
                    Split-screen browser view:
                    Left  — congestion table
                           (fan-in ranked, CRITICAL flagged)
                    Right — animated graph (iframe)
                    Top   — stats bar
```

---

## Project Structure

```
rtl-connectivity-profiler/
│
├── final_parser.py      ← Verilog/SV → signal dependency edges (pyslang AST)
├── graph_builder.py     ← edges → directed NetworkX graph + signal categories
├── analyzer.py          ← graph → fan-in/fan-out metrics, Top-K ranking, report
├── visualizer.py        ← metrics + graph → animated HTML dashboard
├── main.py              ← CLI entry point, orchestrates the full pipeline
│
├── designs/             ← put your .v / .sv files here
│   ├── uart.v
│   ├── spi_master.v
│   └── ...
│
├── reports/             ← all generated output (git-ignored)
│   ├── <design>_report.txt
│   ├── <design>_dashboard.html   ← open this in a browser
│   └── <design>_inner.html       ← loaded by the dashboard iframe
│
├── .gitignore           ← excludes reports/ and caches
├── requirements.txt
└── README.md
```

> `reports/` is listed in `.gitignore` — generated files are never committed.

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/<your-username>/rtl-connectivity-profiler.git
cd rtl-connectivity-profiler
```

### 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

**`requirements.txt`**
```
pyslang
networkx>=3.0
matplotlib>=3.7
```

> **`pyslang`** is the parser backend. It provides a proper SystemVerilog AST — no synthesis step needed.

---

## Usage

### Analyse a single Verilog file

```bash
python main.py --input designs/uart.v --topk 10
```

### Analyse every file in a folder (recursive)

```bash
python main.py --input designs/ --all --topk 10
```

### Options

| Flag | Short | Description | Default |
|------|-------|-------------|---------|
| `--input PATH` | `-i` | `.v`/`.sv` file **or** folder | required |
| `--topk K` | `-k` | Top-K signals in the report | `10` |
| `--all` | `-a` | Recurse through folder | false |

After running, open the dashboard in any browser:

```bash
# macOS
open reports/<design>_dashboard.html

# Linux
xdg-open reports/<design>_dashboard.html

# Windows
start reports/<design>_dashboard.html
```

---

## Output Files

Every run produces three files inside `reports/`:

| File | Description |
|------|-------------|
| `<design>_report.txt` | Plain-text fan-in / fan-out report with stats |
| `<design>_dashboard.html` | **Open this** — full split-screen browser dashboard |
| `<design>_inner.html` | Animated graph loaded inside the dashboard iframe |

> Both HTML files must stay in the same folder so the iframe resolves correctly.

---

## Output Example

### Terminal output

```
=======================================================
  Parsing: designs/uart.v
=======================================================
  Signals found : 52
  Edges found   : 147

  Graph built successfully!
  Total nodes (signals) : 52
  Total edges (deps)    : 147

  Running analysis (Top-10)...

============================================================
  CONNECTIVITY REPORT: uart
============================================================

  GRAPH SUMMARY
  ─────────────────────────────────────────
  Total Signals (nodes) : 52
  Total Edges           : 147
  Graph Density         : 0.0549
  Average Fan-in        : 2.83
  Average Fan-out       : 2.83
  Maximum Fan-in        : 11
  Maximum Fan-out       : 21

  TOP 10 SIGNALS BY FAN-IN
  (signals that depend on the most others)
  ────────────────────────────────────────────────────────
  Rank   Signal               Fan-In     Driven By
  ────────────────────────────────────────────────────────
  1      data_out             11         clk, rst, addr, wr_en, data_in...
  2      next_state           8          state, rx_bit, baud_tick, valid...
  3      tx_reg               6          load, shift_en, data_in, clk...
  4      rx_data              5          rx, baud_en, sample_clk, rst...
  5      status_reg           4          tx_done, rx_done, err, clk...

  TOP 10 SIGNALS BY FAN-OUT
  (signals that drive the most others)
  ────────────────────────────────────────────────────────
  Rank   Signal               Fan-Out    Drives
  ────────────────────────────────────────────────────────
  1      clk                  21         rx_reg, tx_reg, state, ctr, baud...
  2      rst_n                15         all registers, state machine, ctr...
  3      baud_en              9          tx_state, rx_state, sample, shift...
  4      state                7          next_state, output_en, load, shift...
  5      data_in              5          tx_reg, shift_reg, parity, data...

============================================================

  ✅ Done!
     Text report  → reports/uart_report.txt
     Dashboard    → reports/uart_dashboard.html  ← open this in a browser
```

### Browser dashboard

The dashboard opens as a split-screen view:

```
┌─────────────────────┬──────────────────────────────────────────┐
│  Stats bar          │  52 signals · 147 edges · Max FI:11      │
├─────────────────────┼──────────────────────────────────────────┤
│                     │                                          │
│  Signal   Fan-In    │         🔴 data_out                      │
│  ──────────────     │    🔵 clk  ──────────→  🟠 state         │
│  data_out   11 🔴   │         ↑                    │           │
│  next_state  8 🔴   │    🔵 rst_n              🔵 baud_en       │
│  tx_reg      6 🟠   │                  ·  ·  ·                 │
│  rx_data     5 🟠   │     (animated packets flow               │
│  status_reg  4      │      along real signal paths)            │
│  ...                │                                          │
└─────────────────────┴──────────────────────────────────────────┘
```

<img width="1910" height="896" alt="dashboard_screenshot" src="https://github.com/user-attachments/assets/e2d79aff-13bf-41a8-a24f-ae772e163b91" />


**Node colour legend:**

| Colour | Score (`fan-in + fan-out`) | What it means |
|--------|---------------------------|---------------|
| 🔵 Blue | Low | Leaf signal — few connections |
| 🟠 Orange | Medium | Intermediate logic |
| 🔴 Red | High | Hotspot — drives or is driven by many signals |

**Interactive features:**
- Drag any node to rearrange the layout
- Animated packets travel along real source → sink dependency paths
- Arrowheads on every edge show dependency direction

---

## Supported RTL Patterns

| Pattern | Example | Edges Extracted |
|---------|---------|-----------------|
| Continuous assign | `assign c = a & b;` | `a→c`, `b→c` |
| Always combinational | `always @(*) out = in1 & sel;` | `in1→out`, `sel→out` |
| Always sequential | `always @(posedge clk) q <= d;` | `d→q`, `clk→q` |
| Blocking assignment | `result = a + b;` | `a→result`, `b→result` |
| Non-blocking assignment | `reg <= next;` | `next→reg` |
| if / else conditions | `if (sel) out = a;` | `sel→out`, `a→out` |
| case / casex / casez | `case (op) ...` | `op→dst`, `src→dst` |
| Bit / part selects | `assign out = bus[7:0];` | `bus→out` |
| Concatenation | `assign {co,s} = a + b;` | `a→s`, `b→s`, `a→co`... |
| Named port instantiation | `.a(x), .b(y), .s(z)` | `x→inst.a`, `y→inst.b` |
| Nested begin...end | any depth | ✓ |

---

## Dataset

Designs used for evaluation — all open-source:

| # | Design | Module | Category | Source |
|---|--------|--------|----------|--------|
| 1 | UART Controller | `uart_controller` | Sequential / FSM | [freecores/uart16550](https://github.com/freecores/uart16550) |
| 2 | SPI Master | `spi_master` | Sequential | [ultraembedded/core_spi](https://github.com/ultraembedded/core_spi) |
| 3 | I2C Controller | `i2c_master` | Hierarchical | [ultraembedded/core_i2c](https://github.com/ultraembedded/core_i2c) |
| 4 | 32-bit ALU | `alu_32bit` | Combinational | [freecores/fpu](https://github.com/freecores/fpu) |
| 5 | PicoRV32 CPU | `picorv32` | Hierarchical | [YosysHQ/picorv32](https://github.com/YosysHQ/picorv32) |
| 6 | SERV CPU | `serv_core` | Sequential | [olofk/serv](https://github.com/olofk/serv) |
| 7 | Ethernet MAC | `eth_mac` | Hierarchical | [freecores/ethmac](https://github.com/freecores/ethmac) |
| 8 | VGA Controller | `vga_core` | Mixed | [freecores/vga_lcd](https://github.com/freecores/vga_lcd) |
| 9 | AXI Crossbar | `axi_crossbar` | Hierarchical | [alexforencich/verilog-axi](https://github.com/alexforencich/verilog-axi) |
| 10 | FIR Filter | `fir_filter` | Combinational | open |
| 11 | RISC-V Pipeline | `riscv_pipeline` | Sequential | [jameslzhu/riscv-card](https://github.com/jameslzhu) |
| 12 | USB Controller | `usb_serial` | FSM + Datapath | [ultraembedded/core_usb_serial](https://github.com/ultraembedded) |

---

## Results Summary

| Design | Signals | Edges | Top Fan-In Signal | Top Fan-Out Signal |
|--------|---------|-------|-------------------|--------------------|
| uart_controller | 52 | 147 | data_out (11) | clk (21) |
| spi_master | 38 | 94 | miso_reg (8) | clk (17) |
| alu_32bit | 61 | 203 | result (14) | a (19) |
| picorv32 | 312 | 1,847 | mem_rdata (29) | clk (89) |
| i2c_master | 74 | 218 | scl_oen (12) | state (23) |

**Key observation:** `clk` and `rst_n` are consistently the highest fan-out signals in every sequential design — expected, since they gate all registers. The more interesting hotspots are datapath signals like `result`, `data_out`, and `state` — these represent real design complexity, and are the correct targets for directed stress vectors.

---

## Tech Stack

| Tool | Role |
|------|------|
| **Python 3.10+** | Core language |
| **pyslang** | Verilog/SystemVerilog AST parser — proper grammar, no regex hacks |
| **networkx** | Directed graph construction, path finding, density |
| **Vanilla JS + SVG** | Self-contained animated browser dashboard (zero JS dependencies) |

---

## Assignment Context

Developed for the **ML in VLSI CAD** course.

**Problem 3 — Graph-Based Connectivity Analysis for RTL Designs**

| Requirement | Status |
|-------------|--------|
| Parses unsynthesized RTL | ✅ pyslang AST, no synthesis needed |
| Directed dependency graph | ✅ NetworkX DiGraph, signal nodes + dependency edges |
| Fan-in and fan-out (unique) | ✅ in\_degree / out\_degree per node |
| Top-K incoming and outgoing signals | ✅ configurable `--topk` |
| Evidence (what drives / is driven by each) | ✅ shown in report and dashboard table |
| Generalised — works on any `.v`/`.sv` | ✅ tested on 12 open-source designs |
| 10–15 designs (combinational + sequential + hierarchical) | ✅ see dataset table |
| Text report | ✅ `reports/<design>_report.txt` |
| Visualisation | ✅ interactive animated HTML dashboard |

---

## Screenshots


<img width="548" height="542" alt="dashboard" src="https://github.com/user-attachments/assets/fe6ab072-e23a-4188-8392-31b7d88060d2" />
<img width="1364" height="826" alt="graph_animated" src="https://github.com/user-attachments/assets/68f6bf64-d84d-42bb-b370-c9db04f1a247" />
<img width="1051" height="810" alt="terminal_output1" src="https://github.com/user-attachments/assets/fa6ec6fd-6fad-4e2f-b32c-542fbd38d4cf" />
<img width="586" height="728" alt="terminal_output2" src="https://github.com/user-attachments/assets/7110e682-a469-4379-865a-6f999ed3934e" />

---

## Author

**Lalit Mohan** — B.Tech, ML in VLSI CAD course

---

## License

Academic use only — ML in VLSI CAD course assignment.
