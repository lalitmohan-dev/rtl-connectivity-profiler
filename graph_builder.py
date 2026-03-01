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

    # DiGraph = Directed Graph (arrows have direction)
    G = nx.DiGraph()

    for (source, destination) in edges:
        # add_edge automatically adds nodes too
        # if they don't exist yet
        G.add_edge(source, destination)

    print(f"\n  Graph built successfully!")
    print(f"  Total nodes (signals) : {G.number_of_nodes()}")
    print(f"  Total edges (deps)    : {G.number_of_edges()}")

    return G


# ══════════════════════════════════════════
# EXTRA INFO — Get signal categories
# ══════════════════════════════════════════

def get_signal_info(G, filepath):
    """
    Categorize every signal in the graph:
        - input port    (no incoming edges)
        - output port   (no outgoing edges)
        - internal wire (has both)
        - isolated      (no edges at all)

    This helps us understand the graph better.
    """

    info = {
        "inputs"    : [],   # signals with no predecessors
        "outputs"   : [],   # signals with no successors
        "internal"  : [],   # signals with both
        "isolated"  : [],   # signals completely alone
    }

    for node in G.nodes():
        has_incoming = G.in_degree(node)  > 0
        has_outgoing = G.out_degree(node) > 0

        if     has_incoming and     has_outgoing:
            info["internal"].append(node)
        elif   has_incoming and not has_outgoing:
            info["outputs"].append(node)
        elif not has_incoming and   has_outgoing:
            info["inputs"].append(node)
        else:
            info["isolated"].append(node)

    return info


# ══════════════════════════════════════════
# SAVE AND LOAD — Store graph to file
# ══════════════════════════════════════════

def save_graph(G, output_path):
    """
    Save the graph to a file so you
    don't have to rebuild it every time.

    Uses GraphML format — readable by
    many tools including Gephi.
    """
    nx.write_graphml(G, output_path)
    print(f"  Graph saved → {output_path}")


def load_graph(input_path):
    """
    Load a previously saved graph.
    """
    G = nx.read_graphml(input_path)
    print(f"  Graph loaded ← {input_path}")
    return G


# ══════════════════════════════════════════
# TEST IT
# ══════════════════════════════════════════

if __name__ == "__main__":

    # Simulate what final_parser.py gives us
    # (replace this with real parser output later)
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

    # Build the graph
    G = build_graph(test_edges)

    # Get signal categories
    info = get_signal_info(G, "test.v")

    print(f"\n  Signal categories:")
    print(f"    Input-like  signals : {info['inputs']}")
    print(f"    Output-like signals : {info['outputs']}")
    print(f"    Internal    signals : {info['internal']}")
    print(f"    Isolated    signals : {info['isolated']}")

    # Save the graph
    save_graph(G, "test_graph.graphml")

    print("\n  ✅ graph_builder.py works correctly!")