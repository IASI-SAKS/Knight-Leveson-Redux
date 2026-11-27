#!/usr/bin/env python3

import argparse
import csv
import sys
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(
        description="Build a cross-test heatmap from the output of computeStatsTCTS."
    )
    parser.add_argument("input_file", help="Input CSV file (output of computeStatsTCTS)")
    parser.add_argument(
        "-o", "--outdir",
        default=".",
        help="Output directory for the heatmap (default: current directory)"
    )
    parser.add_argument(
        "-f", "--format",
        choices=["png", "html"],
        default="png",
        help="Output format: 'png' for static image, 'html' for interactive (default: png)"
    )
    parser.add_argument(
        "-s", "--minScale",
        type=float,
        default=None,
        help="Minimum value for the heatmap color scale (default: min value in data)"
    )
    parser.add_argument(
        "-S", "--maxScale",
        type=float,
        default=None,
        help="Maximum value for the heatmap color scale (default: max value in data)"
    )
    return parser.parse_args()


def read_statistics(input_file: Path) -> dict[tuple[str, str], float]:
    """Read the statistics CSV and aggregate Number of True Cross Tests by (Source, Target) pair."""
    matrix: dict[tuple[str, str], float] = {}

    with open(input_file, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            source = row["Source Implementation"].strip()
            target = row["Target Implementation"].strip()
            try:
                count = float(row["Number of True Cross Tests"])
            except (ValueError, KeyError):
                count = 0.0
            key = (source, target)
            matrix[key] = matrix.get(key, 0.0) + count

    return matrix


def build_matrix(matrix: dict[tuple[str, str], float]):
    """Build sorted sources, targets and 2D value grid."""
    sources = sorted(set(s for s, _ in matrix))
    targets = sorted(set(t for _, t in matrix))
    grid = [
        [matrix.get((source, target), 0.0) for target in targets]
        for source in sources
    ]
    return sources, targets, grid


def save_png(sources, targets, grid, output_path: Path, vmin=None, vmax=None):
    """Save heatmap as a PNG image using seaborn and matplotlib."""
    import matplotlib.pyplot as plt
    import seaborn as sns

    fig, ax = plt.subplots(
        figsize=(max(6, len(targets) * 1.2), max(5, len(sources) * 1.0))
    )

    # Use a custom annotation that trims unnecessary trailing zeros
    import numpy as np
    grid_np = np.array(grid)
    annot = np.where(
        grid_np == grid_np.astype(int),
        grid_np.astype(int).astype(str),
        np.vectorize(lambda v: f"{v:.2f}".rstrip("0"))(grid_np)
    )

    sns.heatmap(
        grid_np,
        annot=annot,
        fmt="",
        cmap="YlOrRd",
        xticklabels=targets,
        yticklabels=sources,
        linewidths=0.5,
        vmin=vmin,
        vmax=vmax,
        ax=ax
    )

    ax.set_title("True Cross Tests Heatmap", fontsize=14, pad=12)
    ax.set_xlabel("Target Implementation", fontsize=11)
    ax.set_ylabel("Source Implementation", fontsize=11)
    plt.xticks(rotation=45, ha="right", fontsize=9)
    plt.yticks(rotation=0, fontsize=9)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()


def save_html(sources, targets, grid, output_path: Path, vmin=None, vmax=None):
    """Save an interactive heatmap as a self-contained HTML file using D3.js."""
    import json

    # Build flat list of {source, target, value} for D3
    data = [
        {"source": sources[i], "target": targets[j], "value": grid[i][j]}
        for i in range(len(sources))
        for j in range(len(targets))
    ]

    all_values = [d["value"] for d in data]
    scale_min = vmin if vmin is not None else min(all_values, default=0)
    scale_max = vmax if vmax is not None else max(all_values, default=1)

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>True Cross Tests Heatmap</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.8.5/d3.min.js"></script>
    <style>
        body {{ font-family: sans-serif; margin: 40px; }}
        h2 {{ text-align: center; }}
        .tooltip {{
            position: absolute;
            background: rgba(0,0,0,0.75);
            color: #fff;
            padding: 6px 10px;
            border-radius: 4px;
            font-size: 13px;
            pointer-events: none;
            opacity: 0;
        }}
        .axis text {{ font-size: 12px; }}
    </style>
</head>
<body>
    <h2>True Cross Tests Heatmap</h2>
    <div id="heatmap"></div>
    <div class="tooltip" id="tooltip"></div>
    <script>
        const data    = {json.dumps(data)};
        const sources = {json.dumps(sources)};
        const targets = {json.dumps(targets)};

        const margin = {{ top: 30, right: 100, bottom: 120, left: 160 }};
        const cellSize = 60;
        const width  = targets.length * cellSize;
        const height = sources.length * cellSize;

        const svg = d3.select("#heatmap")
            .append("svg")
            .attr("width",  width  + margin.left + margin.right)
            .attr("height", height + margin.top  + margin.bottom)
            .append("g")
            .attr("transform", `translate(${{margin.left}},${{margin.top}})`);

        const x = d3.scaleBand().domain(targets).range([0, width]).padding(0.05);
        const y = d3.scaleBand().domain(sources).range([0, height]).padding(0.05);

        const minVal = {json.dumps(scale_min)};
        const maxVal = {json.dumps(scale_max)};
        const color  = d3.scaleSequential(d3.interpolateYlOrRd).domain([minVal, maxVal]);

        // Axes
        svg.append("g")
            .attr("transform", `translate(0,${{height}})`)
            .call(d3.axisBottom(x))
            .selectAll("text")
            .attr("transform", "rotate(-40)")
            .style("text-anchor", "end");

        svg.append("g").call(d3.axisLeft(y));

        // Axis labels
        svg.append("text")
            .attr("x", width / 2)
            .attr("y", height + margin.bottom - 10)
            .attr("text-anchor", "middle")
            .style("font-size", "13px")
            .text("Target Implementation");

        svg.append("text")
            .attr("transform", "rotate(-90)")
            .attr("x", -height / 2)
            .attr("y", -margin.left + 20)
            .attr("text-anchor", "middle")
            .style("font-size", "13px")
            .text("Source Implementation");

        // Tooltip
        const tooltip = d3.select("#tooltip");

        // Cells
        svg.selectAll("rect")
            .data(data)
            .enter().append("rect")
            .attr("x", d => x(d.target))
            .attr("y", d => y(d.source))
            .attr("width",  x.bandwidth())
            .attr("height", y.bandwidth())
            .attr("fill", d => color(d.value))
            .on("mouseover", (event, d) => {{
                tooltip.style("opacity", 1)
                    .html(`Source: <b>${{d.source}}</b><br>Target: <b>${{d.target}}</b><br>Count: <b>${{d.value}}</b>`);
            }})
            .on("mousemove", event => {{
                tooltip.style("left", (event.pageX + 12) + "px")
                       .style("top",  (event.pageY - 28) + "px");
            }})
            .on("mouseout", () => tooltip.style("opacity", 0));

        // Cell labels
        svg.selectAll("text.cell")
            .data(data)
            .enter().append("text")
            .attr("class", "cell")
            .attr("x", d => x(d.target) + x.bandwidth() / 2)
            .attr("y", d => y(d.source) + y.bandwidth() / 2 + 5)
            .attr("text-anchor", "middle")
            .style("font-size", "12px")
            .style("fill", d => d.value > maxVal * 0.6 ? "#fff" : "#333")
            .text(d => Number.isInteger(d.value) ? d.value : parseFloat(d.value.toFixed(2)));

        // Color bar
        const legendHeight = height;
        const legendWidth  = 15;
        const legendX      = width + 30;

        const legendScale = d3.scaleLinear().domain([minVal, maxVal]).range([legendHeight, 0]);
        const legendAxis  = d3.axisRight(legendScale).ticks(5);

        const defs = svg.append("defs");
        const linearGradient = defs.append("linearGradient")
            .attr("id", "legend-gradient")
            .attr("x1", "0%").attr("y1", "100%")
            .attr("x2", "0%").attr("y2", "0%");

        d3.range(0, 1.01, 0.1).forEach(t => {{
            linearGradient.append("stop")
                .attr("offset", `${{t * 100}}%`)
                .attr("stop-color", color(minVal + t * (maxVal - minVal)));
        }});

        svg.append("rect")
            .attr("x", legendX)
            .attr("y", 0)
            .attr("width",  legendWidth)
            .attr("height", legendHeight)
            .style("fill", "url(#legend-gradient)");

        svg.append("g")
            .attr("transform", `translate(${{legendX + legendWidth}}, 0)`)
            .call(legendAxis);
    </script>
</body>
</html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)


def main():
    args = parse_args()

    input_file = Path(args.input_file)
    if not input_file.is_file():
        print(f"Error: '{input_file}' is not a valid file.", file=sys.stderr)
        sys.exit(1)

    outdir = Path(args.outdir)
    if not outdir.is_dir():
        print(f"Error: output directory '{outdir}' does not exist.", file=sys.stderr)
        sys.exit(1)

    print(f"Reading statistics from '{input_file}' ...")
    matrix = read_statistics(input_file)

    sources, targets, grid = build_matrix(matrix)
    print(f"Found {len(sources)} source(s) and {len(targets)} target(s).")

    stem = input_file.stem
    output_path = outdir / f"heatmap_{stem}.{args.format}"

    if args.format == "png":
        save_png(sources, targets, grid, output_path, vmin=args.minScale, vmax=args.maxScale)
    else:
        save_html(sources, targets, grid, output_path, vmin=args.minScale, vmax=args.maxScale)

    print(f"Heatmap saved to: {output_path.resolve()}")


if __name__ == "__main__":
    main()
