from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from statistics import mean
from textwrap import fill
from typing import Any

os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/bogp_mpl_cache")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


OP_COLOR = "#D8E8F7"
VAR_COLOR = "#DCEED8"
CONST_COLOR = "#F8E2C4"
EDGE_COLOR = "#5A6472"
TEXT_COLOR = "#20242A"


def _node_label(node: dict[str, Any]) -> str:
    op = str(node.get("op", "?"))
    if op == "var":
        index = node.get("variable_index")
        return f"x{int(index) + 1}" if index is not None else "x?"
    if op == "const":
        value = node.get("value")
        return f"const\n{float(value):.4g}" if value is not None else "const"
    if op == "div":
        return "protected\ndiv"
    return op


def _node_color(node: dict[str, Any]) -> str:
    op = str(node.get("op", "?"))
    if op == "var":
        return VAR_COLOR
    if op == "const":
        return CONST_COLOR
    return OP_COLOR


def _expression(node: dict[str, Any]) -> str:
    op = str(node.get("op", "?"))
    children = list(node.get("children", []))
    if op == "var":
        index = node.get("variable_index")
        return f"x{int(index) + 1}" if index is not None else "x?"
    if op == "const":
        return f"{float(node.get('value')):.12g}"
    if op == "add":
        return f"({_expression(children[0])} + {_expression(children[1])})"
    if op == "sub":
        return f"({_expression(children[0])} - {_expression(children[1])})"
    if op == "mul":
        return f"({_expression(children[0])} * {_expression(children[1])})"
    if op == "div":
        return f"protected_div({_expression(children[0])}, {_expression(children[1])})"
    if op == "sin":
        return f"sin({_expression(children[0])})"
    if op == "cos":
        return f"cos({_expression(children[0])})"
    return f"{op}(" + ", ".join(_expression(child) for child in children) + ")"


def _assign_layout(
    node: dict[str, Any],
    *,
    depth: int,
    positions: dict[int, tuple[float, float]],
    nodes: list[tuple[int, dict[str, Any]]],
    edges: list[tuple[int, int]],
    next_leaf_x: list[float],
    next_id: list[int],
) -> int:
    node_id = next_id[0]
    next_id[0] += 1
    nodes.append((node_id, node))

    child_ids: list[int] = []
    child_x_values: list[float] = []
    for child in node.get("children", []):
        child_id = _assign_layout(
            child,
            depth=depth + 1,
            positions=positions,
            nodes=nodes,
            edges=edges,
            next_leaf_x=next_leaf_x,
            next_id=next_id,
        )
        child_ids.append(child_id)
        child_x_values.append(positions[child_id][0])
        edges.append((node_id, child_id))

    if child_x_values:
        x_value = mean(child_x_values)
    else:
        x_value = next_leaf_x[0]
        next_leaf_x[0] += 1.0
    positions[node_id] = (float(x_value), float(-depth))
    return node_id


def _plot_tree(payload: dict[str, Any], output_path: Path) -> None:
    item = payload["items"][0]
    tree = item["tree"]
    expression = item.get("expression", "")
    objectives = item.get("objective_values", {})

    positions: dict[int, tuple[float, float]] = {}
    nodes: list[tuple[int, dict[str, Any]]] = []
    edges: list[tuple[int, int]] = []
    _assign_layout(
        tree,
        depth=0,
        positions=positions,
        nodes=nodes,
        edges=edges,
        next_leaf_x=[0.0],
        next_id=[0],
    )

    leaf_count = max(1.0, max(x for x, _ in positions.values()) + 1.0)
    max_depth = max(-y for _, y in positions.values())
    width = max(12.0, leaf_count * 0.85)
    height = max(8.0, (max_depth + 1.0) * 1.25)
    fig, ax = plt.subplots(figsize=(width, height))

    for parent, child in edges:
        x_parent, y_parent = positions[parent]
        x_child, y_child = positions[child]
        ax.plot(
            [x_parent, x_child],
            [y_parent, y_child],
            color=EDGE_COLOR,
            linewidth=1.4,
            zorder=1,
        )

    for node_id, node in nodes:
        x_value, y_value = positions[node_id]
        ax.text(
            x_value,
            y_value,
            _node_label(node),
            ha="center",
            va="center",
            fontsize=9,
            color=TEXT_COLOR,
            bbox={
                "boxstyle": "round,pad=0.32",
                "facecolor": _node_color(node),
                "edgecolor": "#30343B",
                "linewidth": 1.0,
            },
            zorder=2,
        )

    train = objectives.get("train_nrmse")
    size = objectives.get("tree_size")
    test = item.get("test_nrmse")
    title = (
        "BO-controlled GP Pareto solution with maximum tree size "
        f"(seed={item.get('seed')})\n"
        f"train_nrmse={float(train):.6f}, test_nrmse={float(test):.6f}, tree_size={float(size):.0f}"
    )
    ax.set_title(title, fontsize=14, pad=18)
    ax.text(
        0.5,
        -0.08,
        fill("Expression: " + expression, width=150),
        ha="center",
        va="top",
        transform=ax.transAxes,
        fontsize=9,
        color=TEXT_COLOR,
    )
    ax.set_axis_off()
    ax.set_xlim(-0.8, leaf_count - 0.2)
    ax.set_ylim(-(max_depth + 0.7), 0.7)
    fig.tight_layout()
    fig.savefig(output_path, dpi=240, bbox_inches="tight")
    plt.close(fig)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Extracted solution JSON path.")
    parser.add_argument("--output", required=True, help="Output figure path.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    _plot_tree(payload, output_path)
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
