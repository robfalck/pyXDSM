from typing import TYPE_CHECKING, Optional, Union

if TYPE_CHECKING:
    from pyxdsm.XDSM import XDSM

from pyxdsm.xdsm_latex_writer import _chunk_label, _sanitize_tikz_name


class XDSMMermaidWriter:
    """
    Writer class for generating Mermaid.js block-beta output from XDSM diagrams.
    """

    @staticmethod
    def _sanitize_name(name: str) -> str:
        return _sanitize_tikz_name(name)

    @staticmethod
    def _format_label(label: Union[str, list, tuple], label_width: Optional[int] = None) -> str:
        if isinstance(label, (list, tuple)):
            if label_width is None:
                inner = r" \\ ".join(str(item) for item in label)
            else:
                labels = []
                for chunk in _chunk_label(label, label_width):
                    labels.append(", ".join(str(item) for item in chunk))
                inner = r" \\ ".join(labels)
            return f'"$$\\begin{{array}}{{c}} {inner} \\end{{array}}$$"'
        else:
            return f'"$${label}$$"'

    @staticmethod
    def write(xdsm: "XDSM", file_name: Optional[str] = None) -> None:
        borders = {
            "Optimization": ("(", ")"),
            "DOE": ("(", ")"),
            "MDA": ("([", "])"),
            "Function": ("[", "]"),
            "ImplicitFunction": ("[", "]"),
            "Metamodel": ("[", "]"),
            "Group": ("{{", "}}"),
            "ImplicitGroup": ("{{", "}}"),
            "SubOptimization": ("{{", "}}"),
            "DataInter": ("[/", "/]"),
            "DataIO": ("[/", "/]"),
        }

        color_map = {
            "Optimization": "#A0CBE8",
            "DOE": "#A0CBE8",
            "MDA": "#FFBE7D",
            "Function": "#8CD17D",
            "ImplicitFunction": "#FF9D9A",
            "Metamodel": "#F1CE63",
            "Group": "#8CD17D",
            "ImplicitGroup": "#FF9D9A",
            "SubOptimization": "#A0CBE8",
            "DataInter": "#E6E6E6",
            "DataIO": "#FFFFFF",
            "Conn": "#F0F0F0",
        }

        sys_names = [s.node_name for s in xdsm.systems]
        sys_idx = {name: i for i, name in enumerate(sys_names)}

        num_systems = len(sys_names)
        num_columns = num_systems + 2

        lines = ["%%{init: {'flowchart': {'htmlLabels': true}, 'theme': 'base', 'themeVariables': {'primaryColor':'#fff', 'primaryBorderColor':'#333', 'lineColor':'#CCC'}}}%%"]
        lines.append("block")
        lines.append(f"  columns {num_columns}")

        # Gather connections mapping
        conn_map = {}
        for conn in xdsm.connections:
            if conn.src in sys_idx and conn.target in sys_idx:
                src_i = sys_idx[conn.src]
                tgt_i = sys_idx[conn.target]
                conn_map[(src_i, tgt_i)] = conn

        # Gather left and right outputs mapping
        left_outs = {}
        right_outs = {}
        for comp_name, node in xdsm.outputs.items():
            if comp_name in sys_idx:
                i = sys_idx[comp_name]
                if node.side == "left":
                    left_outs[i] = node
                else:
                    right_outs[i] = node

        used_classes = set()
        node_class_assignments = []

        for i, sys_node in enumerate(xdsm.systems):
            row_items = []

            # 1. Left output
            if i in left_outs:
                out_node = left_outs[i]
                l_b, r_b = borders.get("DataIO", ("[/", "/]"))
                lbl = XDSMMermaidWriter._format_label(out_node.label, out_node.label_width)
                node_id = f"left_output_{i}"
                row_items.append(f"{node_id}{l_b}{lbl}{r_b}")
                node_class_assignments.append(f"  class {node_id} DataIO")
                used_classes.add("DataIO")
            else:
                row_items.append("space")

            # 2. Main systems and connections
            for j in range(num_systems):
                if i == j:
                    l_b, r_b = borders.get(sys_node.style, ("[", "]"))
                    lbl = XDSMMermaidWriter._format_label(sys_node.label, sys_node.label_width)
                    node_id = XDSMMermaidWriter._sanitize_name(sys_node.node_name)
                    row_items.append(f"{node_id}{l_b}{lbl}{r_b}")
                    node_class_assignments.append(f"  class {node_id} {sys_node.style}")
                    used_classes.add(sys_node.style)
                elif (i, j) in conn_map:
                    conn = conn_map[(i, j)]
                    l_b, r_b = borders.get("DataInter", ("[/", "/]"))
                    lbl = XDSMMermaidWriter._format_label(conn.label, conn.label_width)
                    node_id = f"conn_{i}_{j}"
                    row_items.append(f"{node_id}{l_b}{lbl}{r_b}")
                    node_class_assignments.append(f"  class {node_id} Conn")
                    used_classes.add("Conn")
                else:
                    row_items.append("space")

            # 3. Right output
            if i in right_outs:
                out_node = right_outs[i]
                l_b, r_b = borders.get("DataIO", ("[/", "/]"))
                lbl = XDSMMermaidWriter._format_label(out_node.label, out_node.label_width)
                node_id = f"right_output_{i}"
                row_items.append(f"{node_id}{l_b}{lbl}{r_b}")
                node_class_assignments.append(f"  class {node_id} DataIO")
                used_classes.add("DataIO")
            else:
                row_items.append("space")

            lines.append("  " + " ".join(row_items))

        lines.append("")

        # Draw edges for connections
        # Group connections by source and sort by target index
        connections_by_src = {}
        for (src_i, tgt_i) in conn_map:
            if src_i not in connections_by_src:
                connections_by_src[src_i] = []
            connections_by_src[src_i].append(tgt_i)
        for src_i in connections_by_src:
            connections_by_src[src_i].sort()

        # Group connections by target (incoming connections)
        connections_by_tgt = {}
        for (src_i, tgt_i) in conn_map:
            if tgt_i not in connections_by_tgt:
                connections_by_tgt[tgt_i] = []
            connections_by_tgt[tgt_i].append(src_i)
        for tgt_i in connections_by_tgt:
            connections_by_tgt[tgt_i].sort()

        # Draw edges, routing through intermediate connection nodes for long connections
        for (src_i, tgt_i), conn in conn_map.items():
            src_name = XDSMMermaidWriter._sanitize_name(sys_names[src_i])
            tgt_name = XDSMMermaidWriter._sanitize_name(sys_names[tgt_i])

            # If connection spans multiple columns or rows, route through intermediate connection nodes
            if tgt_i - src_i > 1:
                # Build connection path through intermediate connection nodes that actually exist
                conn_path = [src_name]
                for target_j in connections_by_src[src_i]:
                    conn_path.append(f"conn_{src_i}_{target_j}")
                    if target_j == tgt_i:
                        break

                # Add intermediate connection nodes in the vertical direction if they exist
                for row_k in range(src_i + 1, tgt_i):
                    if (row_k, tgt_i) in conn_map:
                        conn_path.append(f"conn_{row_k}_{tgt_i}")

                conn_path.append(tgt_name)

                # Draw edges along the path
                for i in range(len(conn_path) - 1):
                    lines.append(f"  {conn_path[i]} --- {conn_path[i+1]}")
            else:
                # Direct connection between adjacent systems
                conn_id = f"conn_{src_i}_{tgt_i}"

                # For feedback connections (src_i > tgt_i), route through intermediate connection nodes
                if src_i > tgt_i and tgt_i in connections_by_tgt:
                    # Find all sources feeding back to this target that are between current source and target
                    intermediate_sources = [s for s in connections_by_tgt[tgt_i] if tgt_i < s < src_i]
                    intermediate_sources.sort(reverse=True)  # Sort descending to go from higher to lower row

                    # Build path through intermediate connection nodes
                    conn_path = [src_name, conn_id]
                    for inter_src in intermediate_sources:
                        conn_path.append(f"conn_{inter_src}_{tgt_i}")
                    conn_path.append(tgt_name)

                    # Draw edges along the path
                    for i in range(len(conn_path) - 1):
                        lines.append(f"  {conn_path[i]} --- {conn_path[i+1]}")
                elif tgt_i in connections_by_tgt and len(connections_by_tgt[tgt_i]) > 1 and src_i < tgt_i:
                    # For feedforward connections with multiple incoming sources, route vertically through them
                    incoming_sources = connections_by_tgt[tgt_i]
                    current_src_idx = incoming_sources.index(src_i)

                    # Build vertical path through incoming connection nodes up to and including this one
                    conn_path = [src_name, conn_id]

                    # Add intermediate connection nodes between this source and the next
                    for next_idx in range(current_src_idx + 1, len(incoming_sources)):
                        next_src = incoming_sources[next_idx]
                        conn_path.append(f"conn_{next_src}_{tgt_i}")

                    conn_path.append(tgt_name)

                    # Draw edges along the path
                    for i in range(len(conn_path) - 1):
                        lines.append(f"  {conn_path[i]} --- {conn_path[i+1]}")
                else:
                    # Simple direct path
                    lines.append(f"  {src_name} --- {conn_id}")
                    lines.append(f"  {conn_id} --- {tgt_name}")

        # Draw edges for outputs
        for i in left_outs:
            src_name = XDSMMermaidWriter._sanitize_name(sys_names[i])
            node_id = f"left_output_{i}"

            # Route through outgoing connections to systems on the left (feedback connections)
            leftward_connections = []
            if i in connections_by_src:
                for j in connections_by_src[i]:
                    if j < i:
                        leftward_connections.append(j)

            if leftward_connections:
                # Build path through connections
                conn_path = [src_name]
                for j in leftward_connections:
                    conn_path.append(f"conn_{i}_{j}")
                conn_path.append(node_id)

                # Draw edges along the path
                for k in range(len(conn_path) - 1):
                    lines.append(f"  {conn_path[k]} --- {conn_path[k+1]}")
            else:
                # Direct connection if no intermediate connections
                lines.append(f"  {src_name} --- {node_id}")

        for i in right_outs:
            src_name = XDSMMermaidWriter._sanitize_name(sys_names[i])
            node_id = f"right_output_{i}"

            # Route through outgoing connections to systems on the right (feedforward connections)
            rightward_connections = []
            if i in connections_by_src:
                for j in connections_by_src[i]:
                    if j > i:
                        rightward_connections.append(j)

            if rightward_connections:
                # Build path through connections
                conn_path = [src_name]
                for j in rightward_connections:
                    conn_path.append(f"conn_{i}_{j}")
                conn_path.append(node_id)

                # Draw edges along the path
                for k in range(len(conn_path) - 1):
                    lines.append(f"  {conn_path[k]} --- {conn_path[k+1]}")
            else:
                # Direct connection if no intermediate connections
                lines.append(f"  {src_name} --- {node_id}")

        lines.append("")
        for cls_name in sorted(used_classes):
            hex_color = color_map.get(cls_name, "#FFFFFF")
            lines.append(f"  classDef {cls_name} fill:{hex_color},stroke:#333,stroke-width:1px")

        lines.append("")
        lines.extend(node_class_assignments)

        mermaid_text = "\n".join(lines)

        if file_name is None:
            print(mermaid_text)
        elif file_name.endswith(".html"):
            html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>XDSM Mermaid Diagram</title>
    <script type="module">
      import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs';
      mermaid.initialize({{ startOnLoad: true }});
    </script>
</head>
<body>
    <pre class="mermaid">
{mermaid_text}
    </pre>
</body>
</html>"""
            with open(file_name, "w", encoding="utf-8") as f:
                f.write(html_content)
        else:
            with open(file_name, "w", encoding="utf-8") as f:
                f.write(mermaid_text)
