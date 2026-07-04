"""
Architecture Assistant — auto-generated dependency reports, sequence
narratives, and impact summaries, built entirely on top of the existing
Knowledge Graph (graphdb.py) and processing-sequence connectors
(peoplecode.py). No new graph engine or diagram renderer: reports are
Markdown text, diagrams are Mermaid code blocks a human can paste into any
Mermaid-compatible viewer (GitHub, Mermaid Live Editor, Obsidian, etc.).
"""

from connectors import graphdb, uom, peoplecode


def _node_label(node: dict) -> str:
    if not node:
        return "?"
    return f"{node.get('type')}:{node.get('name')}"


def dependency_report(env: str, node_type: str, node_name: str, depth: int = 3) -> dict:
    """
    Compose a Markdown dependency/impact document for one object:
    Overview, Depends On (forward), Depended On By (reverse/blast radius),
    Direct Relationships (typed edges) — the same data /admin/impact and the
    graph_dependencies/graph_impact AI tools already expose, packaged as a
    readable document.
    """
    node_id = graphdb.node_id(node_type, node_name)
    depth = max(1, min(int(depth), 4))
    result = graphdb.impact(env, node_id, depth=depth)

    if not result.get("found"):
        return {
            "found": False,
            "markdown": f"# Dependency Report: {node_type}:{node_name}\n\n"
                        f"No such object found in the {env} knowledge graph. "
                        f"Rebuild the graph or confirm the object name.\n",
        }

    node = result["node"]
    forward = result["forward_deps"].get("nodes", [])
    reverse = result["reverse_deps"].get("nodes", [])
    forward_edges = result["forward_deps"].get("edges", [])
    summary = result["summary"]

    lines = [
        f"# Dependency Report: {node.get('display_name', node_name)}",
        "",
        f"**Type:** {node.get('type')}  ",
        f"**Environment:** {env}  ",
        f"**Traversal depth:** {depth}",
        "",
        "## Overview",
        "",
        f"- Downstream (depends on): **{summary['total_downstream']}** objects",
        f"- Upstream (depended on by): **{summary['total_upstream']}** objects",
        "",
    ]

    lines.append("## Depends On (forward)")
    lines.append("")
    if forward:
        for otype, count in summary["forward_by_type"].items():
            lines.append(f"- {otype}: {count}")
        lines.append("")
        lines.append("| Object | Type |")
        lines.append("|---|---|")
        for n in forward[:100]:
            lines.append(f"| {n.get('display_name', n.get('name'))} | {n.get('type')} |")
    else:
        lines.append("_No forward dependencies found at this depth._")
    lines.append("")

    lines.append("## Depended On By (blast radius)")
    lines.append("")
    if reverse:
        for otype, count in summary["reverse_by_type"].items():
            lines.append(f"- {otype}: {count}")
        lines.append("")
        lines.append("| Object | Type |")
        lines.append("|---|---|")
        for n in reverse[:100]:
            lines.append(f"| {n.get('display_name', n.get('name'))} | {n.get('type')} |")
    else:
        lines.append("_Nothing else in the graph depends on this object at this depth._")
    lines.append("")

    lines.append("## Direct Relationships")
    lines.append("")
    if forward_edges:
        lines.append("| Relationship | Target |")
        lines.append("|---|---|")
        seen = set()
        for e in forward_edges[:100]:
            key = (e.get("type"), e.get("target"))
            if key in seen:
                continue
            seen.add(key)
            lines.append(f"| {e.get('type')} | {e.get('target')} |")
    else:
        lines.append("_No direct typed edges recorded._")
    lines.append("")

    return {"found": True, "node": node, "markdown": "\n".join(lines)}


def sequence_narrative(env: str, target_type: str, name: str) -> dict:
    """
    Render a Component/Record's canonical processing sequence as both a
    phase-ordered narrative and a Mermaid flowchart code block, reusing
    peoplecode.py's existing component_sequence()/record_sequence() —
    no new sequencing logic, just a different presentation of it.
    """
    target_type = target_type.lower()
    if target_type == "component":
        data = peoplecode.component_sequence(env, name)
        title = f"Component Processing Sequence: {data.get('component', name)}"
    elif target_type == "record":
        data = peoplecode.record_sequence(env, name)
        title = f"Record Processing Sequence: {data.get('record', name)}"
    else:
        return {"found": False, "markdown": f"# Sequence Report\n\nUnsupported target_type '{target_type}' — use 'component' or 'record'.\n"}

    phases = data.get("phases", [])
    if not phases:
        return {"found": False, "markdown": f"# {title}\n\nNo processing sequence data found.\n"}

    lines = [f"# {title}", "", f"**Environment:** {env}", ""]

    mermaid = ["```mermaid", "flowchart TD"]
    prev_id = None
    node_n = 0
    for phase in phases:
        lines.append(f"## {phase['label']}")
        lines.append("")
        lines.append(f"_{phase.get('desc', '')}_")
        lines.append("")
        for ev in phase.get("events", []):
            status = ev.get("status", "empty")
            marker = {"delivered": "✓ delivered", "custom": "⚠ custom", "empty": "— empty"}.get(status, status)
            lines.append(f"- **{ev['name']}** ({marker}){' — ' + ev['note'] if ev.get('note') else ''}")
            if status != "empty":
                node_n += 1
                node_key = f"N{node_n}"
                safe_label = ev["name"].replace('"', "'")
                mermaid.append(f'    {node_key}["{safe_label}<br/>({status})"]')
                if prev_id:
                    mermaid.append(f"    {prev_id} --> {node_key}")
                prev_id = node_key
        lines.append("")

    mermaid.append("```")

    lines.append("## Diagram")
    lines.append("")
    lines.extend(mermaid)
    lines.append("")

    return {"found": True, "markdown": "\n".join(lines)}


def impact_summary_doc(env: str, node_type: str, node_name: str, depth: int = 2) -> dict:
    """
    Prose-formatted blast-radius summary for pasting into a change ticket —
    same graphdb.impact() data as the /admin/impact UI, phrased as sentences.
    """
    node_id = graphdb.node_id(node_type, node_name)
    depth = max(1, min(int(depth), 4))
    result = graphdb.impact(env, node_id, depth=depth)

    if not result.get("found"):
        return {"found": False, "markdown": f"No object `{node_type}:{node_name}` found in the {env} knowledge graph."}

    node = result["node"]
    summary = result["summary"]
    upstream = summary["total_upstream"]
    downstream = summary["total_downstream"]

    parts = [
        f"**Impact Summary — {node.get('display_name', node_name)} ({node.get('type')}, {env})**",
        "",
    ]
    if upstream == 0:
        parts.append("Nothing else in the knowledge graph currently depends on this object — "
                      "changing it carries no detected downstream blast radius.")
    else:
        by_type = ", ".join(f"{c} {t}" for t, c in summary["reverse_by_type"].items())
        parts.append(f"Changing this object could affect **{upstream}** other object(s): {by_type}. "
                      f"Review these before making changes.")
    parts.append("")
    if downstream:
        by_type = ", ".join(f"{c} {t}" for t, c in summary["forward_by_type"].items())
        parts.append(f"This object itself depends on **{downstream}** other object(s): {by_type}.")

    return {"found": True, "markdown": "\n".join(parts)}
