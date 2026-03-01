# final_parser.py
# Parses any Verilog/SystemVerilog file
# Returns a set of (source, destination) signal edges
#
# Usage:
#   from final_parser import parse_verilog
#   edges = parse_verilog("yourfile.v")

import pyslang
import json
import os


# ══════════════════════════════════════════
# PART A — Convert Verilog file to JSON dict
# ══════════════════════════════════════════

def verilog_to_dict(filepath):
    """
    Read a .v or .sv file using pyslang
    Convert the AST tree into a plain Python dictionary
    Much easier to work with than the pyslang tree directly
    """
    tree = pyslang.SyntaxTree.fromFile(filepath)

    def node_to_dict(node):
        # Leaf node (Token) — just save kind and value
        if isinstance(node, pyslang.Token):
            return {
                "kind":  str(node.kind),
                "value": str(node.value)
            }
        # Branch node — save kind and all children
        return {
            "kind":     str(node.kind),
            "children": [node_to_dict(child) for child in node]
        }

    return node_to_dict(tree.root)


# ══════════════════════════════════════════
# PART B — Helper Functions
# ══════════════════════════════════════════

def get_all_names(node):
    """
    Collect ALL signal names from any node.

    Walks the dictionary tree recursively.
    Whenever it finds a TokenKind.Identifier — grabs the name.

    Example:
        give it node for "a & b"
        returns ["a", "b"]
    """
    names = []

    if not isinstance(node, dict):
        return names

    kind  = node.get("kind",  "")
    value = node.get("value", "")

    # BASE CASE — found an identifier token
    # This is an actual signal name — grab it and stop
    if kind == "TokenKind.Identifier":
        if value and not value[0].isdigit():
            names.append(value)
        return names

    # RECURSIVE CASE — keep walking into children
    for child in node.get("children", []):
        names.extend(get_all_names(child))

    return names


def find_all_nodes(node, kind_string):
    """
    Search entire tree for nodes whose kind
    contains kind_string.

    Example:
        find_all_nodes(ast, "AlwaysBlock")
        returns list of all always block nodes
    """
    found = []

    if not isinstance(node, dict):
        return found

    # Does THIS node match?
    if kind_string in node.get("kind", ""):
        found.append(node)

    # Check all children too
    for child in node.get("children", []):
        found.extend(find_all_nodes(child, kind_string))

    return found


# ══════════════════════════════════════════
# PART C — Edge Extraction Functions
# ══════════════════════════════════════════

def edges_from_assignment(node):
    """
    Extract edges from ONE assignment node.

    Works for both:
        assign d = a & b     (blocking)
        c <= a | b           (nonblocking)

    Rule:
        children[0] = LEFT SIDE  = destination
        children[1] = operator (= or <=) — SKIP
        children[2+]= RIGHT SIDE = sources

    Returns list of (source, destination) tuples
    """
    edges    = []
    children = node.get("children", [])

    if len(children) < 3:
        return edges

    # LEFT side — destination signals
    left_node  = children[0]
    dest_names = get_all_names(left_node)

    # RIGHT side — source signals (skip index 1 = operator)
    source_names = []
    for right_node in children[2:]:
        source_names.extend(get_all_names(right_node))

    # Make edges: each source → each destination
    for dest in dest_names:
        for src in source_names:
            if src != dest:
                edges.append((src, dest))

    return edges


def edges_from_always(node):
    """
    Extract edges from ONE always block.

    Handles both:
        always @(posedge clk) — sequential (has clock)
        always @(*)           — combinational (no clock)

    Steps:
        1. Find sensitivity signals (clk, rst)
        2. Find all assignments inside
        3. Add data edges (a→c, b→c)
        4. Add clock edges (clk→c) for sequential blocks
    """
    edges = []

    # Step 1: Get sensitivity signals
    # SignalEventExpression = @(posedge clk) type
    sens_signals = []
    for sens_node in find_all_nodes(node, "SignalEventExpression"):
        sens_signals.extend(get_all_names(sens_node))

    # Step 2 & 3: Get all assignments + data edges
    all_destinations = []

    for assign in find_all_nodes(node, "AssignmentExpression"):
        assign_edges = edges_from_assignment(assign)
        edges.extend(assign_edges)

        # Remember destinations for clock edges
        children = assign.get("children", [])
        if children:
            dests = get_all_names(children[0])
            all_destinations.extend(dests)

    # Step 4: Add sensitivity → destination edges
    # Only for clocked blocks (not @(*))
    for sens in sens_signals:
        for dest in all_destinations:
            if sens != dest:
                edges.append((sens, dest))

    return edges


# ══════════════════════════════════════════
# PART D — Clean Up Garbage
# ══════════════════════════════════════════

def clean_edges(edges):
    """
    Remove edges that contain garbage values.

    Things that are NOT real signals:
        - Numbers: 0, 1, 2
        - Verilog constants: 1'b0, 1'b1
        - Keywords: begin, end, if, else
        - Anything starting with a digit
    """
    IGNORE = {
        '0', '1', '2', '3', '4', '5', '6', '7', '8', '9',
        'x', 'z',
        'begin', 'end', 'if', 'else',
        'case', 'default', 'for', 'while',
        'integer', 'genvar',
    }

    def is_real_signal(name):
        if not name:                return False
        if name in IGNORE:          return False
        if name[0].isdigit():       return False
        if "'" in name:             return False   # 1'b0 style
        if name.startswith("__"):   return False   # internal
        return True

    cleaned = set()
    for src, dst in edges:
        if is_real_signal(src) and is_real_signal(dst):
            cleaned.add((src, dst))

    return cleaned


# ══════════════════════════════════════════
# PART E — MAIN FUNCTION
# This is what main.py imports and calls
# ══════════════════════════════════════════

def parse_verilog(filepath, save_json=False):
    """
    *** MAIN FUNCTION ***

    Give it any .v or .sv Verilog file.
    Get back a set of (source, destination) edges.

    Example:
        edges = parse_verilog("ALU.v")
        # returns {("operandA", "resultR"), ("opcode", "PSR"), ...}

    Optional:
        save_json=True  →  also saves the AST as a .json file
                           useful for debugging in VS Code

    Steps inside:
        1. Read file with pyslang
        2. Convert AST to Python dictionary
        3. Find all assignment patterns
        4. Extract signal dependency edges
        5. Clean up garbage values
        6. Return clean set of edges
    """

    print(f"\n{'=' * 50}")
    print(f"  Parsing: {filepath}")
    print(f"{'=' * 50}")

    # Safety check — does file exist?
    if not os.path.exists(filepath):
        print(f"  ERROR: File not found — {filepath}")
        return set()

    try:
        # Step 1 & 2: Read + convert to dictionary
        ast = verilog_to_dict(filepath)

        # Optional: save JSON for inspection in VS Code
        if save_json:
            json_path = filepath.replace('.v',  '.json') \
                                .replace('.sv', '.json')
            with open(json_path, 'w') as f:
                json.dump(ast, f, indent=2)
            print(f"  AST saved → {json_path}")

        # Step 3 & 4: Extract edges from all patterns
        edges = []

        # Pattern A: continuous assign (assign d = a & b)
        assign_nodes = find_all_nodes(ast, "AssignmentExpression")
        for node in assign_nodes:
            edges.extend(edges_from_assignment(node))

        # Pattern B & C: always blocks (@(posedge clk) and @(*))
        always_nodes = find_all_nodes(ast, "AlwaysBlock")
        for node in always_nodes:
            edges.extend(edges_from_always(node))

        # Step 5: Clean garbage
        clean = clean_edges(edges)

        # Summary
        all_signals = set()
        for src, dst in clean:
            all_signals.add(src)
            all_signals.add(dst)

        print(f"  Signals found : {len(all_signals)}")
        print(f"  Edges found   : {len(clean)}")

        return clean

    except Exception as e:
        print(f"  ERROR parsing {filepath}: {e}")
        return set()


# ══════════════════════════════════════════
# RUN AS STANDALONE TEST
# ══════════════════════════════════════════

if __name__ == "__main__":

    # Test on ALU file
    test_file = "ALU_verilog.v"

    # Fall back to test.v if ALU not found
    if not os.path.exists(test_file):
        test_file = "test.v"

    if not os.path.exists(test_file):
        print("No test file found. Create test.v first.")
    else:
        # Parse and save JSON for inspection
        edges = parse_verilog(test_file, save_json=True)

        print(f"\nFinal Edge List ({len(edges)} edges):")
        print("-" * 40)
        for src, dst in sorted(edges):
            print(f"  {src:20s}  →  {dst}")