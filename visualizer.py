import os
import json
from pyvis.network import Network
import json


def visualize_interactive(G, results, output_path):

    # =============================
    # Compute Fanin / Fanout
    # =============================
    nodes = []
    max_score = 1

    for n in G.nodes():

        fanin = G.in_degree(n)
        fanout = G.out_degree(n)
        score = fanin + fanout

        max_score = max(max_score, score)

        nodes.append({
            "id": str(n),
            "label": str(n),
            "fanin": fanin,
            "fanout": fanout,
            "score": score
        })

    edges = [[str(a), str(b)] for a, b in G.edges()]

    # ---------- routing paths ----------
    sources = [n for n, d in G.in_degree() if d == 0]
    sinks = [n for n, d in G.out_degree() if d == 0]

    paths = []

    for s in sources[:5]:
        for t in sinks[:5]:
            try:
                p = list(nx.all_simple_paths(G, s, t, cutoff=6))
                paths.extend(p[:3])
            except:
                pass

    if not paths:
        paths = [list(G.nodes())]

    # =============================
    # HTML
    # =============================
    html = """
<!DOCTYPE html>
<html>
<head>

<style>

body{
margin:0;
background:#020617;
overflow:hidden;
font-family:sans-serif;
}

.stage{
width:100vw;
height:100vh;
position:relative;
}

.node{
position:absolute;
width:130px;
height:55px;
border-radius:8px;
color:white;
font-size:11px;
display:flex;
flex-direction:column;
align-items:center;
justify-content:center;
cursor:grab;
}

.packet{
position:absolute;
width:10px;
height:10px;
border-radius:50%;
background:#38bdf8;
box-shadow:0 0 10px #38bdf8;
transform:translate(-50%,-50%);
}

svg{
position:absolute;
inset:0;
}

</style>
</head>

<body>

<div class="stage" id="stage">
<svg id="links"></svg>
</div>

<script>

const nodesData = __NODES__;
const edgesData = __EDGES__;
const pathsData = __PATHS__;
const MAX_SCORE = __MAX__;

const stage=document.getElementById("stage");
const svg=document.getElementById("links");

svg.setAttribute("width","100%");
svg.setAttribute("height","100%");

const nodeMap={};
const nodeElems={};


// ===================
// STATIC COLOR
// ===================
function getColor(score){

let v = score / MAX_SCORE;

let r = Math.floor(255*v);
let g = Math.floor(180*(1-v));
let b = Math.floor(255*(1-v));

return "rgb("+r+","+g+","+b+")";
}


// ===================
// CREATE NODES
// ===================
nodesData.forEach(function(n){

n.x=Math.random()*900+40;
n.y=Math.random()*500+40;

n.vx=(Math.random()-0.5)*1.2;
n.vy=(Math.random()-0.5)*1.2;

const d=document.createElement("div");
d.className="node";

d.style.background=getColor(n.score);

d.innerHTML=
"<b>"+n.label+"</b>"+
"<div>IN:"+n.fanin+
" OUT:"+n.fanout+"</div>";

stage.appendChild(d);

nodeMap[n.id]=n;
nodeElems[n.id]=d;

// drag
let drag=false;

d.onpointerdown=function(e){
drag=true;
d.setPointerCapture(e.pointerId);
n.vx=0;n.vy=0;
};

d.onpointermove=function(e){
if(!drag)return;
n.x=e.clientX-65;
n.y=e.clientY-25;
};

d.onpointerup=function(){
drag=false;
n.vx=Math.random()-0.5;
n.vy=Math.random()-0.5;
};

});


// ===================
// LINKS
// ===================
const lines=edgesData.map(function(e){

const L=document.createElementNS(
"http://www.w3.org/2000/svg","line");

L.setAttribute("stroke","#334155");
svg.appendChild(L);

return {a:e[0],b:e[1],line:L};

});


// ===================
// PACKET MOTION
// ===================
function lerp(a,b,t){
return a+(b-a)*t;
}

function createPacket(){

let routeIDs=
pathsData[Math.floor(Math.random()*pathsData.length)];

let route=routeIDs.map(id=>nodeMap[id]);

const pkt=document.createElement("div");
pkt.className="packet";
stage.appendChild(pkt);

let seg=0;
let t=0;

function move(){

let p0=route[seg];
let p1=route[seg+1];

if(!p1){
pkt.remove();
return;
}

pkt.style.left=
lerp(p0.x+65,p1.x+65,t)+"px";

pkt.style.top=
lerp(p0.y+25,p1.y+25,t)+"px";

t+=0.02;

if(t>=1){
seg++;
t=0;
}

requestAnimationFrame(move);
}

move();
}

setInterval(createPacket,250);


// ===================
// ANIMATION LOOP
// ===================
function animate(){

let w=stage.clientWidth;
let h=stage.clientHeight;

nodesData.forEach(function(n){

n.x+=n.vx;
n.y+=n.vy;

if(n.x<0||n.x>w-130)n.vx*=-1;
if(n.y<0||n.y>h-55)n.vy*=-1;

nodeElems[n.id].style.left=n.x+"px";
nodeElems[n.id].style.top=n.y+"px";

});

lines.forEach(function(l){

let p1=nodeMap[l.a];
let p2=nodeMap[l.b];

l.line.setAttribute("x1",p1.x+65);
l.line.setAttribute("y1",p1.y+25);
l.line.setAttribute("x2",p2.x+65);
l.line.setAttribute("y2",p2.y+25);

});

requestAnimationFrame(animate);
}

animate();

</script>

</body>
</html>
"""

    html = html.replace("__NODES__", json.dumps(nodes))
    html = html.replace("__EDGES__", json.dumps(edges))
    html = html.replace("__PATHS__", json.dumps(paths))
    html = html.replace("__MAX__", str(max_score))

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print("✅ Packet + FanIn/FanOut visualization saved")

def generate_final_report(results, graph_html_filename, output_path, threshold=20):
    """Generates the split-screen Dashboard with a Congestion Table."""
    top_fanin = results['top_fanin']
    max_val = results['stats']['max_fanin'] or 1
    
    table_rows = ""
    for e in top_fanin:
        is_congested = e['count'] >= threshold
        status = "<b style='color:#ef4444'>CRITICAL</b>" if is_congested else "<span style='color:#10b981'>STABLE</span>"
        row_bg = "background: rgba(239, 68, 68, 0.1);" if is_congested else ""
        
        table_rows += f'''
        <tr style="{row_bg} border-bottom: 1px solid #1e293b;">
            <td style="padding: 12px;">{e['signal']}</td>
            <td style="padding: 12px; font-weight: bold;">{e['count']}</td>
            <td style="padding: 12px;">{status}</td>
        </tr>'''

    html_content = f"""
    <html>
    <head>
        <style>
            body {{ margin: 0; background: #020617; color: white; font-family: sans-serif; display: flex; height: 100vh; overflow: hidden; }}
            #sidebar {{ width: 380px; background: #0f172a; border-right: 2px solid #1e293b; padding: 20px; overflow-y: auto; }}
            #main {{ flex-grow: 1; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 13px; }}
            th {{ text-align: left; color: #94a3b8; padding: 10px; border-bottom: 2px solid #334155; }}
            iframe {{ width: 100%; height: 100%; border: none; }}
        </style>
    </head>
    <body>
        <div id="sidebar">
            <h2 style="color:#60a5fa; margin-bottom:5px;">RTL Flow Analysis</h2>
            <p style="font-size:12px; color:#94a3b8;">Threshold: {threshold} inputs. Red indicates congestion.</p>
            <table>
                <thead><tr><th>Signal</th><th>Fan-In</th><th>Status</th></tr></thead>
                <tbody>{table_rows}</tbody>
            </table>
        </div>
        <div id="main"><iframe src="{graph_html_filename}"></iframe></div>
    </body>
    </html>"""
    
    with open(output_path, 'w') as f:
        f.write(html_content)