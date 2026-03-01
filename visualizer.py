# visualizer.py
# Generates two output files per design:
#   1. <design>_inner.html     — animated signal-flow graph (self-contained)
#   2. <design>_dashboard.html — split-screen dashboard with congestion table
#
# Bugs fixed vs original:
#   - Added missing `import networkx as nx` (caused NameError crash)
#   - Removed unused `import os`, duplicate `import json`, dead `pyvis` import
#   - Node spawn area now uses window.innerWidth/Height (was hardcoded 900×500)
#   - Node velocity reduced 1.2 → 0.45 (was too fast to read labels)
#   - MAX_PACKETS=30 cap added (was unbounded — DOM bloat after ~2 min)
#   - Packet t-increment now distance-scaled (was fixed → inconsistent speed)
#   - SVG arrowhead <marker> added (edges were direction-less plain lines)
#   - Bounce logic uses Math.abs() so nodes never get stuck at walls
#   - iframe src prefixed with "./" for reliable cross-platform resolution
#   - generate_final_report now prints a confirmation line on save
#   - Dead variable `max_val` removed from generate_final_report
#
# Usage:
#   from visualizer import visualize_interactive, generate_final_report

import json
import networkx as nx   # FIX: was missing entirely — caused NameError


# ══════════════════════════════════════════════════════════════
# ANIMATED GRAPH
# ══════════════════════════════════════════════════════════════

def visualize_interactive(G, results, output_path):
    """
    Write a fully self-contained animated HTML file that shows
    the signal dependency graph with:
      • Colour-coded nodes  (red = high fan-in+out, blue = low)
      • Draggable nodes     (grab and reposition freely)
      • Gentle physics      (slow bounce, readable labels)
      • Signal packets      (travel along real source→sink paths)
      • SVG arrowheads      (edge direction clearly visible)
      • Packet cap          (max 30 live, no DOM bloat)
      • Distance-scaled speed (packets move at constant visual velocity)
    """

    # ── Node data ──
    nodes     = []
    max_score = 1

    for n in G.nodes():
        fanin  = G.in_degree(n)
        fanout = G.out_degree(n)
        score  = fanin + fanout
        max_score = max(max_score, score)
        nodes.append({
            "id"    : str(n),
            "label" : str(n),
            "fanin" : fanin,
            "fanout": fanout,
            "score" : score,
        })

    edge_list = [[str(a), str(b)] for a, b in G.edges()]

    # ── Packet animation paths (source → sink) ──
    sources = [n for n, d in G.in_degree()  if d == 0]
    sinks   = [n for n, d in G.out_degree() if d == 0]

    paths = []
    for s in sources[:5]:
        for t in sinks[:5]:
            try:
                found = list(nx.all_simple_paths(G, s, t, cutoff=6))
                paths.extend(found[:3])
            except Exception:
                pass

    if not paths:
        paths = [list(G.nodes())]   # fallback: use all nodes as one route

    paths_str = [[str(nid) for nid in p] for p in paths]

    # ── Fill template ──
    html = _ANIMATED_GRAPH_TEMPLATE
    html = html.replace("__NODES__",     json.dumps(nodes))
    html = html.replace("__EDGES__",     json.dumps(edge_list))
    html = html.replace("__PATHS__",     json.dumps(paths_str))
    html = html.replace("__MAX_SCORE__", str(max_score))

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"  Graph animation saved → {output_path}")


# ══════════════════════════════════════════════════════════════
# HTML TEMPLATE
# ══════════════════════════════════════════════════════════════

_ANIMATED_GRAPH_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>RTL Signal Graph</title>
<style>
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

body {
  background: #020617;
  overflow: hidden;
  font-family: 'Segoe UI', system-ui, sans-serif;
  width: 100vw;
  height: 100vh;
}

#stage {
  position: relative;
  width: 100%;
  height: 100%;
}

/* SVG layer sits behind node divs */
#svg-layer {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

.node {
  position: absolute;
  width: 120px;
  height: 52px;
  border-radius: 10px;
  border: 1px solid rgba(255,255,255,0.15);
  color: #f1f5f9;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 3px;
  cursor: grab;
  user-select: none;
  z-index: 10;
  transition: box-shadow 0.15s;
}
.node:active { cursor: grabbing; }
.node:hover  { box-shadow: 0 0 16px rgba(255,255,255,0.3); z-index: 20; }

.node .lbl { font-size: 11px; font-weight: 700; max-width: 110px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.node .inf { font-size: 9px;  color: rgba(255,255,255,0.65); }

.packet {
  position: absolute;
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: #38bdf8;
  box-shadow: 0 0 8px #38bdf8, 0 0 18px rgba(56,189,248,0.35);
  transform: translate(-50%, -50%);
  pointer-events: none;
  z-index: 5;
}

#legend {
  position: absolute;
  bottom: 14px;
  left: 14px;
  background: rgba(15,23,42,0.88);
  border: 1px solid #1e293b;
  border-radius: 8px;
  padding: 10px 14px;
  font-size: 11px;
  color: #94a3b8;
  pointer-events: none;
  z-index: 100;
}
#legend h4 { color: #60a5fa; font-size: 12px; margin-bottom: 7px; }
.lr { display: flex; align-items: center; gap: 8px; margin-top: 4px; }
.ld { width: 12px; height: 12px; border-radius: 3px; flex-shrink: 0; }
</style>
</head>
<body>

<div id="stage">
  <svg id="svg-layer">
    <defs>
      <!--
        FIX: arrowhead marker — previously edges had no direction indicator.
        refX=7 places the tip exactly at the shortened line end.
      -->
      <marker id="arr" markerWidth="8" markerHeight="8"
              refX="7" refY="3" orient="auto" markerUnits="userSpaceOnUse">
        <path d="M0,0 L0,6 L8,3 z" fill="#475569"/>
      </marker>
    </defs>
  </svg>
</div>

<div id="legend">
  <h4>Signal Graph</h4>
  <div class="lr"><div class="ld" style="background:#dc2626"></div>High connectivity</div>
  <div class="lr"><div class="ld" style="background:#2563eb"></div>Low connectivity</div>
  <div class="lr"><div class="ld" style="background:#38bdf8;border-radius:50%"></div>Signal packet</div>
  <div style="margin-top:7px;font-size:10px;color:#334155">Drag nodes · packets follow real paths</div>
</div>

<script>
// ── Injected data ──────────────────────────────────────────────
const nodesData = __NODES__;
const edgesData = __EDGES__;
const pathsData = __PATHS__;
const MAX_SCORE = __MAX_SCORE__;

// ── Config ────────────────────────────────────────────────────
const NODE_W      = 120;
const NODE_H      = 52;
const MAX_PACKETS = 30;     // FIX: cap prevents DOM accumulation
const BASE_VEL    = 0.45;   // FIX: was 1.2 — too fast to read labels
const SPAWN_MS    = 320;    // ms between packet spawns
const PKT_PX_S    = 110;    // target packet speed in px/s (~60fps → ~1.83px/frame)

let livePackets = 0;

// ── Node colour: score 0→blue, score MAX→red ──────────────────
function nodeColor(score) {
  const v = Math.min(score / Math.max(MAX_SCORE, 1), 1);
  const r = Math.round(37  + (220 - 37)  * v);
  const g = Math.round(99  + (38  - 99)  * v);
  const b = Math.round(235 + (38  - 235) * v);
  return `rgb(${r},${g},${b})`;
}

// ── Create node divs ──────────────────────────────────────────
const stage    = document.getElementById('stage');
const svgLayer = document.getElementById('svg-layer');
const nodeMap  = {};
const nodeElms = {};

nodesData.forEach(nd => {
  // FIX: use actual window dimensions so nodes spread across full screen
  const W = window.innerWidth  - NODE_W - 60;
  const H = window.innerHeight - NODE_H - 60;
  nd.x = Math.random() * W + 30;
  nd.y = Math.random() * H + 30;

  // FIX: slow, constant-magnitude velocity in random direction
  const angle = Math.random() * Math.PI * 2;
  nd.vx     = Math.cos(angle) * BASE_VEL * (0.7 + Math.random() * 0.3);
  nd.vy     = Math.sin(angle) * BASE_VEL * (0.7 + Math.random() * 0.3);
  nd.pinned = false;

  const div = document.createElement('div');
  div.className       = 'node';
  div.style.background = nodeColor(nd.score);
  div.innerHTML = `<span class="lbl">${nd.label}</span><span class="inf">IN:${nd.fanin}&nbsp; OUT:${nd.fanout}</span>`;

  // Drag
  let dragging = false;
  div.addEventListener('pointerdown', e => {
    dragging = nd.pinned = true;
    nd.vx = nd.vy = 0;
    div.setPointerCapture(e.pointerId);
    e.stopPropagation();
  });
  div.addEventListener('pointermove', e => {
    if (!dragging) return;
    nd.x = e.clientX - NODE_W / 2;
    nd.y = e.clientY - NODE_H / 2;
  });
  div.addEventListener('pointerup', () => {
    dragging = nd.pinned = false;
    const a = Math.random() * Math.PI * 2;
    nd.vx = Math.cos(a) * BASE_VEL;
    nd.vy = Math.sin(a) * BASE_VEL;
  });

  stage.appendChild(div);
  nodeMap[nd.id]  = nd;
  nodeElms[nd.id] = div;
});

// ── Create SVG edges (with arrowheads) ───────────────────────
const lineElms = edgesData.map(([a, b]) => {
  const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
  line.setAttribute('stroke', '#334155');
  line.setAttribute('stroke-width', '1.5');
  line.setAttribute('marker-end', 'url(#arr)');   // FIX: direction arrow
  svgLayer.appendChild(line);
  return { a, b, line };
});

// ── Packet animation ─────────────────────────────────────────
function dist(nA, nB) {
  const dx = (nB.x + NODE_W / 2) - (nA.x + NODE_W / 2);
  const dy = (nB.y + NODE_H / 2) - (nA.y + NODE_H / 2);
  return Math.sqrt(dx * dx + dy * dy) || 1;
}

function spawnPacket() {
  if (livePackets >= MAX_PACKETS) return;  // FIX: hard cap

  const routeIDs = pathsData[Math.floor(Math.random() * pathsData.length)];
  const route    = routeIDs.map(id => nodeMap[id]).filter(Boolean);
  if (route.length < 2) return;

  const pkt = document.createElement('div');
  pkt.className = 'packet';
  stage.appendChild(pkt);
  livePackets++;

  let seg = 0;
  let t   = 0;

  (function step() {
    const p0 = route[seg];
    const p1 = route[seg + 1];

    if (!p1) { pkt.remove(); livePackets--; return; }

    const cx0 = p0.x + NODE_W / 2,  cy0 = p0.y + NODE_H / 2;
    const cx1 = p1.x + NODE_W / 2,  cy1 = p1.y + NODE_H / 2;

    pkt.style.left = (cx0 + (cx1 - cx0) * t) + 'px';
    pkt.style.top  = (cy0 + (cy1 - cy0) * t) + 'px';

    // FIX: scale increment by distance → constant px/frame speed
    // PKT_PX_S px/s ÷ 60fps = px/frame; divide by segment length → t/frame
    t += (PKT_PX_S / 60) / dist(p0, p1);

    if (t >= 1) { t = 0; seg++; }

    requestAnimationFrame(step);
  })();
}

setInterval(spawnPacket, SPAWN_MS);

// ── Physics + edge redraw loop ────────────────────────────────
function animate() {
  const W = stage.clientWidth;
  const H = stage.clientHeight;

  nodesData.forEach(nd => {
    if (nd.pinned) return;

    nd.x += nd.vx;
    nd.y += nd.vy;

    // FIX: Math.abs() guarantees correct sign after bounce
    // (prevents node getting stuck vibrating at a wall)
    if (nd.x <= 0)          { nd.x = 0;           nd.vx =  Math.abs(nd.vx); }
    if (nd.x >= W - NODE_W) { nd.x = W - NODE_W;  nd.vx = -Math.abs(nd.vx); }
    if (nd.y <= 0)          { nd.y = 0;           nd.vy =  Math.abs(nd.vy); }
    if (nd.y >= H - NODE_H) { nd.y = H - NODE_H;  nd.vy = -Math.abs(nd.vy); }

    nodeElms[nd.id].style.left = nd.x + 'px';
    nodeElms[nd.id].style.top  = nd.y + 'px';
  });

  // Redraw edges — shorten at destination so arrowhead lands at node border
  lineElms.forEach(({ a, b, line }) => {
    const nA = nodeMap[a];
    const nB = nodeMap[b];
    if (!nA || !nB) return;

    const x1 = nA.x + NODE_W / 2,  y1 = nA.y + NODE_H / 2;
    const x2 = nB.x + NODE_W / 2,  y2 = nB.y + NODE_H / 2;
    const dx = x2 - x1,  dy = y2 - y1;
    const len = Math.sqrt(dx * dx + dy * dy) || 1;
    const pull = 22;   // px to pull back so arrow sits at node edge

    line.setAttribute('x1', x1);
    line.setAttribute('y1', y1);
    line.setAttribute('x2', x2 - (dx / len) * pull);
    line.setAttribute('y2', y2 - (dy / len) * pull);
  });

  requestAnimationFrame(animate);
}

animate();
</script>
</body>
</html>
"""


# ══════════════════════════════════════════════════════════════
# SPLIT-SCREEN DASHBOARD
# ══════════════════════════════════════════════════════════════

def generate_final_report(results, graph_html_filename, output_path, threshold=20):
    """
    Write the split-screen dashboard HTML.

    Layout:
      top  — stats bar (signals, edges, max fan-in, max fan-out, density)
      left — scrollable congestion table (fan-in ranked, CRITICAL in red)
      right— iframe with the animated graph

    Args:
        results            : dict from analyzer.analyze()
        graph_html_filename: filename only (e.g. 'design_inner.html')
                             must live in the same folder as output_path
        output_path        : where to write the dashboard HTML
        threshold          : fan-in >= this → flagged CRITICAL
    """
    top_fanin = results['top_fanin']
    stats     = results['stats']

    # ── Table rows ──
    table_rows = ""
    for e in top_fanin:
        is_crit  = e['count'] >= threshold
        status   = ("<b style='color:#ef4444'>CRITICAL</b>"
                    if is_crit else
                    "<span style='color:#10b981'>STABLE</span>")
        row_style = "background:rgba(239,68,68,0.07);" if is_crit else ""

        driven_by = ", ".join(e['connected'][:4])
        if len(e['connected']) > 4:
            driven_by += "…"
        driven_by = driven_by or "—"

        table_rows += f"""
        <tr style="{row_style}border-bottom:1px solid #1e293b;">
          <td style="padding:10px 12px;font-weight:600;">{e['signal']}</td>
          <td style="padding:10px 12px;font-weight:700;text-align:center;">{e['count']}</td>
          <td style="padding:10px 12px;text-align:center;">{status}</td>
          <td style="padding:10px 12px;color:#64748b;font-size:11px;">{driven_by}</td>
        </tr>"""

    # ── Stats bar ──
    stat_items = [
        ("Signals",    stats['total_signals']),
        ("Edges",      stats['total_edges']),
        ("Max Fan-in", stats['max_fanin']),
        ("Max Fan-out",stats['max_fanout']),
        ("Density",    stats['density']),
    ]
    stat_html = "".join(
        f"<div class='stat'><div class='sv'>{v}</div><div class='sk'>{k}</div></div>"
        for k, v in stat_items
    )

    # FIX: prefix with "./" so iframe resolves correctly regardless of
    # what directory the browser considers its base path
    iframe_src = f"./{graph_html_filename}"

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>RTL Flow Analysis Dashboard</title>
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: #020617;
    color: white;
    font-family: 'Segoe UI', system-ui, sans-serif;
    display: flex;
    flex-direction: column;
    height: 100vh;
    overflow: hidden;
  }}

  #stats-bar {{
    display: flex;
    background: #0f172a;
    border-bottom: 1px solid #1e293b;
    flex-shrink: 0;
  }}
  .stat {{
    flex: 1;
    padding: 10px 16px;
    text-align: center;
    border-right: 1px solid #1e293b;
  }}
  .stat:last-child {{ border-right: none; }}
  .sv {{ font-size: 20px; font-weight: 700; color: #60a5fa; }}
  .sk {{ font-size: 10px; color: #475569; margin-top: 2px; text-transform: uppercase; letter-spacing: 0.06em; }}

  #body {{
    display: flex;
    flex: 1;
    overflow: hidden;
  }}

  #sidebar {{
    width: 430px;
    flex-shrink: 0;
    background: #0f172a;
    border-right: 2px solid #1e293b;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }}
  #sidebar-hdr {{
    padding: 15px 18px 11px;
    border-bottom: 1px solid #1e293b;
    flex-shrink: 0;
  }}
  #sidebar-hdr h2 {{ color: #60a5fa; font-size: 14px; margin-bottom: 4px; }}
  #sidebar-hdr p  {{ color: #475569; font-size: 11px; }}
  #table-wrap {{ overflow-y: auto; flex: 1; }}

  table {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
  th {{
    text-align: left;
    color: #64748b;
    padding: 8px 12px;
    background: #0f172a;
    border-bottom: 2px solid #1e293b;
    position: sticky;
    top: 0;
    z-index: 1;
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.06em;
  }}
  tr:hover {{ background: rgba(255,255,255,0.03); }}

  #graph-pane {{ flex: 1; }}
  iframe {{ width: 100%; height: 100%; border: none; display: block; }}
</style>
</head>
<body>

<div id="stats-bar">{stat_html}</div>

<div id="body">
  <div id="sidebar">
    <div id="sidebar-hdr">
      <h2>RTL Connectivity Analysis</h2>
      <p>Fan-in &ge; {threshold} = CRITICAL &nbsp;|&nbsp; Top {len(top_fanin)} signals ranked</p>
    </div>
    <div id="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Signal</th><th style="text-align:center;">Fan-In</th>
            <th style="text-align:center;">Status</th><th>Driven By</th>
          </tr>
        </thead>
        <tbody>{table_rows}</tbody>
      </table>
    </div>
  </div>

  <div id="graph-pane">
    <iframe src="{iframe_src}" title="Signal dependency graph"></iframe>
  </div>
</div>

</body>
</html>"""

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    # FIX: was silent before — now confirms save like all other functions
    print(f"  Dashboard saved      → {output_path}")