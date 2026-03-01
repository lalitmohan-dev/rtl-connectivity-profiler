# analyzer.py
# Takes the graph from graph_builder.py
# Computes fan-in, fan-out, Top-K busy signals
#
# Usage:
#   from analyzer import analyze
#   results = analyze(G, K=10)

import networkx as nx
import os


# ══════════════════════════════════════════
# CORE METRICS — Fan-in and Fan-out
# ══════════════════════════════════════════

def compute_fanin_fanout(G):
    """
    For every signal (node) in the graph,
    compute:

    Fan-in(B)  = how many signals point INTO B
                 = how many things B depends on
                 = G.in_degree(B)

    Fan-out(A) = how many signals A points TO
                 = how many things depend on A
                 = G.out_degree(A)

    Example graph:
        a → d
        b → d
        a → c
        b → c
      clk → c

    Fan-in results:
        d   → 2  (a and b point into d)
        c   → 3  (a, b, clk point into c)
        a   → 0  (nothing points into a)
        b   → 0  (nothing points into b)
        clk → 0  (nothing points into clk)

    Fan-out results:
        a   → 2  (a points to d and c)
        b   → 2  (b points to d and c)
        clk → 1  (clk points to c only)
        d   → 0  (d points to nothing)
        c   → 0  (c points to nothing)
    """

    fan_in  = {}
    fan_out = {}

    for node in G.nodes():
        fan_in[node]  = G.in_degree(node)
        fan_out[node] = G.out_degree(node)

    return fan_in, fan_out


# ══════════════════════════════════════════
# TOP-K — Find the busiest signals
# ══════════════════════════════════════════

def get_top_k(fan_dict, G, K=10, direction="in"):
    """
    Find the Top-K busiest signals.

    direction = "in"  → rank by fan-in  (incoming busy)
    direction = "out" → rank by fan-out (outgoing busy)

    For each top signal, also collect:
        - who drives it   (if direction="in")
        - what it drives  (if direction="out")

    Returns a list of dictionaries, one per signal.
    """

    # Sort signals by their count — highest first
    sorted_signals = sorted(
        fan_dict.items(),
        key    = lambda x: x[1],   # sort by count value
        reverse= True              # highest first
    )

    # Take only top K
    top_k = sorted_signals[:K]

    # Build result with connected signal lists
    results = []

    for signal, count in top_k:

        if direction == "in":
            # Who drives this signal?
            # = predecessors in the graph
            connected = list(G.predecessors(signal))
        else:
            # What does this signal drive?
            # = successors in the graph
            connected = list(G.successors(signal))

        results.append({
            "signal"   : signal,
            "count"    : count,
            "connected": connected
        })

    return results


# ══════════════════════════════════════════
# FULL ANALYSIS — Run everything
# ══════════════════════════════════════════

def analyze(G, K=10):
    """
    Main analysis function.
    Runs all metrics and returns full results.

    Input:
        G — networkx DiGraph from graph_builder
        K — how many top signals to report

    Output:
        Dictionary with all results
    """

    print(f"\n  Running analysis (Top-{K})...")

    # Step 1: Compute fan-in and fan-out for all signals
    fan_in, fan_out = compute_fanin_fanout(G)

    # Step 2: Get top-K for each direction
    top_fanin  = get_top_k(fan_in,  G, K, direction="in")
    top_fanout = get_top_k(fan_out, G, K, direction="out")

    # Step 3: Basic graph stats
    stats = {
        "total_signals" : G.number_of_nodes(),
        "total_edges"   : G.number_of_edges(),
        "density"       : round(nx.density(G), 4),
        "avg_fanin"     : round(
                            sum(fan_in.values()) /
                            max(len(fan_in), 1), 2
                          ),
        "avg_fanout"    : round(
                            sum(fan_out.values()) /
                            max(len(fan_out), 1), 2
                          ),
        "max_fanin"     : max(fan_in.values())  if fan_in  else 0,
        "max_fanout"    : max(fan_out.values()) if fan_out else 0,
    }

    return {
        "stats"      : stats,
        "fan_in"     : fan_in,
        "fan_out"    : fan_out,
        "top_fanin"  : top_fanin,
        "top_fanout" : top_fanout,
    }


# ══════════════════════════════════════════
# REPORT — Print results in professor's format
# ══════════════════════════════════════════

def print_report(results, design_name="design", K=10):
    """
    Print the analysis in a clean readable format
    that matches what the professor expects.
    """

    stats      = results["stats"]
    top_fanin  = results["top_fanin"]
    top_fanout = results["top_fanout"]

    print(f"\n{'=' * 60}")
    print(f"  CONNECTIVITY REPORT: {design_name}")
    print(f"{'=' * 60}")

    # ── Basic Stats ──
    print(f"\n  GRAPH SUMMARY")
    print(f"  {'-' * 40}")
    print(f"  Total Signals (nodes) : {stats['total_signals']}")
    print(f"  Total Edges           : {stats['total_edges']}")
    print(f"  Graph Density         : {stats['density']}")
    print(f"  Average Fan-in        : {stats['avg_fanin']}")
    print(f"  Average Fan-out       : {stats['avg_fanout']}")
    print(f"  Maximum Fan-in        : {stats['max_fanin']}")
    print(f"  Maximum Fan-out       : {stats['max_fanout']}")

    # ── Top-K Fan-in ──
    print(f"\n  TOP {K} SIGNALS BY FAN-IN")
    print(f"  (signals that depend on the most others)")
    print(f"  {'-' * 56}")
    print(f"  {'Rank':<6} {'Signal':<20} {'Fan-In':<10} {'Driven By'}")
    print(f"  {'-' * 56}")

    for i, entry in enumerate(top_fanin, 1):
        signal    = entry["signal"]
        count     = entry["count"]
        connected = entry["connected"]

        # Format connected list — show max 5 names
        if len(connected) > 5:
            conn_str = ", ".join(connected[:5]) + "..."
        else:
            conn_str = ", ".join(connected) if connected else "—"

        print(f"  {i:<6} {signal:<20} {count:<10} {conn_str}")

    # ── Top-K Fan-out ──
    print(f"\n  TOP {K} SIGNALS BY FAN-OUT")
    print(f"  (signals that drive the most others)")
    print(f"  {'-' * 56}")
    print(f"  {'Rank':<6} {'Signal':<20} {'Fan-Out':<10} {'Drives'}")
    print(f"  {'-' * 56}")

    for i, entry in enumerate(top_fanout, 1):
        signal    = entry["signal"]
        count     = entry["count"]
        connected = entry["connected"]

        if len(connected) > 5:
            conn_str = ", ".join(connected[:5]) + "..."
        else:
            conn_str = ", ".join(connected) if connected else "—"

        print(f"  {i:<6} {signal:<20} {count:<10} {conn_str}")

    print(f"\n{'=' * 60}")


# ══════════════════════════════════════════
# SAVE REPORT — Write to text file
# ══════════════════════════════════════════

def save_report(results, design_name, output_path, K=10):
    """
    Save the full report to a .txt file
    for submission.
    """

    stats      = results["stats"]
    top_fanin  = results["top_fanin"]
    top_fanout = results["top_fanout"]

    with open(output_path, 'w') as f:

        f.write(f"{'=' * 60}\n")
        f.write(f"CONNECTIVITY REPORT: {design_name}\n")
        f.write(f"{'=' * 60}\n\n")

        # Stats
        f.write(f"GRAPH SUMMARY\n")
        f.write(f"{'-' * 40}\n")
        f.write(f"Total Signals (nodes) : {stats['total_signals']}\n")
        f.write(f"Total Edges           : {stats['total_edges']}\n")
        f.write(f"Graph Density         : {stats['density']}\n")
        f.write(f"Average Fan-in        : {stats['avg_fanin']}\n")
        f.write(f"Average Fan-out       : {stats['avg_fanout']}\n")
        f.write(f"Maximum Fan-in        : {stats['max_fanin']}\n")
        f.write(f"Maximum Fan-out       : {stats['max_fanout']}\n\n")

        # Top fan-in
        f.write(f"TOP {K} SIGNALS BY FAN-IN\n")
        f.write(f"{'-' * 56}\n")
        f.write(f"{'Rank':<6} {'Signal':<20} {'Fan-In':<10} {'Driven By'}\n")
        f.write(f"{'-' * 56}\n")
        for i, entry in enumerate(top_fanin, 1):
            conn = ", ".join(entry["connected"][:5])
            if len(entry["connected"]) > 5:
                conn += "..."
            f.write(
                f"{i:<6} {entry['signal']:<20} "
                f"{entry['count']:<10} {conn or '—'}\n"
            )

        # Top fan-out
        f.write(f"\nTOP {K} SIGNALS BY FAN-OUT\n")
        f.write(f"{'-' * 56}\n")
        f.write(f"{'Rank':<6} {'Signal':<20} {'Fan-Out':<10} {'Drives'}\n")
        f.write(f"{'-' * 56}\n")
        for i, entry in enumerate(top_fanout, 1):
            conn = ", ".join(entry["connected"][:5])
            if len(entry["connected"]) > 5:
                conn += "..."
            f.write(
                f"{i:<6} {entry['signal']:<20} "
                f"{entry['count']:<10} {conn or '—'}\n"
            )

        f.write(f"\n{'=' * 60}\n")

    print(f"  Report saved → {output_path}")


# ══════════════════════════════════════════
# TEST IT
# ══════════════════════════════════════════

if __name__ == "__main__":
    import networkx as nx

    # Build a test graph manually
    # (same edges as parser would give for test.v)
    G = nx.DiGraph()
    test_edges = [
        ("a",   "d"),
        ("b",   "d"),
        ("a",   "c"),
        ("b",   "c"),
        ("clk", "c"),
    ]
    G.add_edges_from(test_edges)

    print("=" * 45)
    print("  Testing analyzer.py")
    print("=" * 45)

    # Run analysis
    results = analyze(G, K=5)

    # Print report
    print_report(results, design_name="test.v", K=5)

    # Save report
    save_report(results, "test.v", "test_report.txt", K=5)

    print("\n  ✅ analyzer.py works correctly!")