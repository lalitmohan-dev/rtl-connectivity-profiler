# main.py
# Connects ALL files together
# Run this on any Verilog file
#
# Usage:
#   python main.py --input designs/ALU.v --topk 10
#   python main.py --input designs/ --all --topk 5

import os
import argparse

# Import our 4 modules
from final_parser  import parse_verilog
from graph_builder import build_graph, save_graph, get_signal_info
from analyzer      import analyze, print_report, save_report
from visualizer    import visualize_interactive,generate_final_report


# ══════════════════════════════════════════
# RUN ON ONE FILE
# ══════════════════════════════════════════

def run_one_file(filepath, K=10):
    design_name = os.path.splitext(os.path.basename(filepath))[0]
    
    # 1. Parse Verilog
    edges = parse_verilog(filepath)
    if not edges: return None
    
    # 2. Build Graph
    G = build_graph(edges)
    
    # 3. Analyze Results
    results = analyze(G, K=K)
    
    # 4. GENERATE ANIMATED GRAPH
    os.makedirs("reports", exist_ok=True)
    graph_inner = f"reports/{design_name}_inner.html"
    visualize_interactive(G, results, graph_inner)
    
    # 5. GENERATE FINAL DASHBOARD WITH TABLE
    dashboard_path = f"reports/{design_name}_dashboard.html"
    # We pass the name of the 'inner' file so the iframe can load it
    generate_final_report(results, f"{design_name}_inner.html", dashboard_path)
    
    print(f"\n  ✅ Sequence Complete!")
    print(f"  Open this dashboard: {dashboard_path}")
    return results


# ══════════════════════════════════════════
# RUN ON ALL FILES IN A FOLDER
# ══════════════════════════════════════════

def run_all_files(folder_path, K=10):
    """
    Run the full pipeline on every .v and .sv
    file found in a folder.
    """

    verilog_files = []
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.endswith('.v') or file.endswith('.sv'):
                verilog_files.append(os.path.join(root, file))

    if not verilog_files:
        print(f"  No .v or .sv files found in {folder_path}")
        return

    print(f"\n  Found {len(verilog_files)} Verilog files")

    all_results = {}
    failed      = []

    for filepath in verilog_files:
        try:
            results = run_one_file(filepath, K=K)
            if results:
                name = os.path.splitext(
                         os.path.basename(filepath)
                       )[0]
                all_results[name] = results
        except Exception as e:
            print(f"  Failed on {filepath}: {e}")
            failed.append(filepath)

    # Summary table
    print(f"\n{'=' * 60}")
    print(f"  SUMMARY — All Designs")
    print(f"{'=' * 60}")
    print(f"  {'Design':<25} {'Signals':>8} {'Edges':>8} {'MaxFanIn':>10} {'MaxFanOut':>10}")
    print(f"  {'-' * 65}")

    for name, res in all_results.items():
        s = res["stats"]
        print(
            f"  {name:<25} "
            f"{s['total_signals']:>8} "
            f"{s['total_edges']:>8} "
            f"{s['max_fanin']:>10} "
            f"{s['max_fanout']:>10}"
        )

    print(f"\n  Processed : {len(all_results)}")
    if failed:
        print(f"  Failed    : {len(failed)}")
        for f in failed:
            print(f"    - {f}")
    print(f"{'=' * 60}")


# ══════════════════════════════════════════
# COMMAND LINE
# ══════════════════════════════════════════

if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="RTL Connectivity Profiler"
    )
    parser.add_argument(
        "--input",  required=True,
        help="Path to .v/.sv file OR folder"
    )
    parser.add_argument(
        "--topk", type=int, default=10,
        help="Number of top signals to report"
    )
    parser.add_argument(
        "--all", action="store_true",
        help="Run on ALL files in folder"
    )

    args = parser.parse_args()

    if args.all or os.path.isdir(args.input):
        run_all_files(args.input, K=args.topk)
    else:
        run_one_file(args.input, K=args.topk)