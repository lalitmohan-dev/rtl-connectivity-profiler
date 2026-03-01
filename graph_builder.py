# graph_builder.py
# Takes edges from final_parser.py
# Builds a networkx directed graph
#
# Usage:
#   from graph_builder import build_graph
#   G = build_graph(edges)

import networkx as nx


# ══════════════════════════════════════════
# MAIN FUNCTION — Build the graph
# ══════════════════════════════════════════

def build_graph(edges):
    """
    Takes a set of (source, destination) pairs
    and builds a directed graph.

    A directed graph means arrows have direction:
        a → d  means "a points to d"
               means "d depends on a"

    Example:
        edges = {("a","d"), ("b","d"), ("clk","c")}

        Graph looks like:
            a ──→ d
            b ──→ d
          clk ──→ c

    Input:
        edges — set of (source, destination) tuples

    Output:
        G — networkx DiGraph object
    """

    G = nx.DiGraph()

    for (source, destination) in edges:
        # add_edge automatically adds nodes too if they don't exist yet
        G.add_edge(source, destination)

    print(f"\n  Graph built successfully!")
    print(f"  Total nodes (signals) : {G.number_of_nodes()}")
    print(f"  Total edges (deps)    : {G.number_of_edges()}")

    return G


# ══════════════════════════════════════════
# EXTRA INFO — Get signal categories
# ══════════════════════════════════════════

def get_signal_info(G):
    """
    Categorize every signal in the graph:
        - input    (no incoming edges  — primary inputs / clocks)
        - output   (no outgoing edges  — primary outputs)
        - internal (has both in and out edges)
        - isolated (no edges at all)

    FIX: removed unused `filepath` parameter from original signature.

    Returns dict with keys: inputs, outputs, internal, isolated
    """

    info = {
        "inputs"  : [],
        "outputs" : [],
        "internal": [],
        "isolated": [],
    }

    for node in G.nodes():
        has_in  = G.in_degree(node)  > 0
        has_out = G.out_degree(node) > 0

        if   has_in and has_out:
            info["internal"].append(node)
        elif has_in:
            info["outputs"].append(node)
        elif has_out:
            info["inputs"].append(node)
        else:
            info["isolated"].append(node)

    return info


# ══════════════════════════════════════════
# SAVE AND LOAD — Store graph to file
# ══════════════════════════════════════════

def save_graph(G, output_path):
    """
    Save the graph to GraphML format.
    Readable by Gephi, yEd, and other graph tools.
    """
    nx.write_graphml(G, output_path)
    print(f"  Graph saved → {output_path}")


def load_graph(input_path):
    """Load a previously saved GraphML graph."""
    G = nx.read_graphml(input_path)
    print(f"  Graph loaded ← {input_path}")
    return G


# ══════════════════════════════════════════
# TEST
# ══════════════════════════════════════════

if __name__ == "__main__":

    test_edges = {
        ("a",   "d"),
        ("b",   "d"),
        ("a",   "c"),
        ("b",   "c"),
        ("clk", "c"),
    }

    print("=" * 45)
    print("  Testing graph_builder.py")
    print("=" * 45)

    G = build_graph(test_edges)

    # FIX: get_signal_info no longer takes filepath
    info = get_signal_info(G)

    print(f"\n  Signal categories:")
    print(f"    Input-like  signals : {info['inputs']}")
    print(f"    Output-like signals : {info['outputs']}")
    print(f"    Internal    signals : {info['internal']}")
    print(f"    Isolated    signals : {info['isolated']}")

    save_graph(G, "/tmp/test_graph.graphml")

    print("\n  ✅ graph_builder.py works correctly!")