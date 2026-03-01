# main.py
# Connects ALL files together
# Run this on any Verilog file
#
# Usage:
#   python main.py --input designs/ALU.v --topk 10
#   python main.py --input designs/ --all --topk 5
#
# Fixes vs original:
#   - get_signal_info() call no longer passes filepath (removed unused param)
#   - Both output HTML files go into the same output folder so the iframe
#     src="./<name>_inner.html" always resolves correctly
#   - print_report + save_report calls restored (were missing in uploaded version)

import os
import argparse

from final_parser  import parse_verilog
from graph_builder import build_graph, save_graph, get_signal_info
from analyzer      import analyze, print_report, save_report
from visualizer    import visualize_interactive, generate_final_report


# ══════════════════════════════════════════
# RUN ON ONE FILE
# ══════════════════════════════════════════

def run_one_file(filepath, K=10):
    """
    Full pipeline for one Verilog file:
        parse → build graph → analyze → report → visualize
    """
    design_name = os.path.splitext(os.path.basename(filepath))[0]

    print(f"\n{'#' * 55}")
    print(f"  Processing : {design_name}")
    print(f"  File       : {filepath}")
    print(f"{'#' * 55}")

    # 1. Parse Verilog → edges
    edges = parse_verilog(filepath)
    if not edges:
        print(f"  ⚠  No edges found — skipping {filepath}")
        return None

    # 2. Build directed graph
    G = build_graph(edges)

    # 3. Analyze (fan-in, fan-out, top-K, stats)
    results = analyze(G, K=K)

    # 4. Print text report to console
    print_report(results, design_name=design_name, K=K)

    # 5. Save text report to file
    os.makedirs("reports", exist_ok=True)
    report_path = f"reports/{design_name}_report.txt"
    save_report(results, design_name, report_path, K=K)

    # 6. Generate animated graph HTML
    # FIX: both HTML files go into reports/ so the iframe src works correctly
    inner_path     = f"reports/{design_name}_inner.html"
    dashboard_path = f"reports/{design_name}_dashboard.html"

    visualize_interactive(G, results, inner_path)

    # Pass only the filename (not the full path) as the iframe src —
    # dashboard and inner file are in the same folder
    generate_final_report(
        results,
        graph_html_filename=f"{design_name}_inner.html",
        output_path=dashboard_path,
    )

    print(f"\n  ✅ Done!")
    print(f"     Text report  → {report_path}")
    print(f"     Dashboard    → {dashboard_path}  ← open this in a browser")

    return results


# ══════════════════════════════════════════
# RUN ON ALL FILES IN A FOLDER
# ══════════════════════════════════════════

def run_all_files(folder_path, K=10):
    """
    Run the full pipeline on every .v and .sv file in a folder.
    Prints a comparative summary table at the end.
    """
    verilog_files = []
    for root, dirs, files in os.walk(folder_path):
        for file in sorted(files):
            if file.endswith('.v') or file.endswith('.sv'):
                verilog_files.append(os.path.join(root, file))

    if not verilog_files:
        print(f"  No .v or .sv files found in {folder_path}")
        return

    print(f"\n  Found {len(verilog_files)} Verilog file(s)")

    all_results = {}
    failed      = []

    for filepath in verilog_files:
        try:
            results = run_one_file(filepath, K=K)
            if results:
                name = os.path.splitext(os.path.basename(filepath))[0]
                all_results[name] = results
        except Exception as e:
            print(f"  ✗ Failed on {filepath}: {e}")
            failed.append(filepath)

    # Summary table
    print(f"\n{'=' * 65}")
    print(f"  BATCH SUMMARY — All Designs")
    print(f"{'=' * 65}")
    print(f"  {'Design':<25} {'Signals':>8} {'Edges':>8} {'MaxFanIn':>10} {'MaxFanOut':>10}")
    print(f"  {'-' * 65}")

    for name, res in sorted(all_results.items()):
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
            print(f"    ✗ {f}")
    print(f"{'=' * 65}")


# ══════════════════════════════════════════
# COMMAND LINE
# ══════════════════════════════════════════

if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="RTL Connectivity Profiler",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--input", "-i", required=True,
        help="Path to a .v/.sv file OR a folder"
    )
    parser.add_argument(
        "--topk", "-k", type=int, default=10,
        help="Number of top signals to report"
    )
    parser.add_argument(
        "--all", "-a", action="store_true",
        help="Process ALL .v/.sv files in the folder (recursive)"
    )

    args = parser.parse_args()

    if args.all or os.path.isdir(args.input):
        run_all_files(args.input, K=args.topk)
    else:
        run_one_file(args.input, K=args.topk)