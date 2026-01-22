from __future__ import annotations

from pathlib import Path
from typing import Optional

import plotly.graph_objects as go


def _build_css(chart_type: str) -> str:
    hover_selectors = [
        ".plotly .sunburst g.slice:hover path",
        ".plotly .treemap g.treemaplayer path:hover",
        ".plotly .treemap path:hover",
    ]
    selectors = ",\n    ".join(hover_selectors)

    controls_css = ""
    if chart_type == "sunburst":
        controls_css = """
.controls-panel {
    position: fixed;
    top: 16px;
    right: 16px;
    z-index: 9999;
    display: flex;
    gap: 8px;
    padding: 10px 12px;
    background: rgba(15, 20, 30, 0.75);
    border-radius: 12px;
    backdrop-filter: blur(8px);
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.25);
    color: #fff;
    font-family: "Segoe UI", "Noto Sans TC", sans-serif;
}
.controls-panel button {
    background: #1f2a44;
    color: #fff;
    border: none;
    border-radius: 8px;
    padding: 6px 10px;
    font-size: 13px;
    cursor: pointer;
    transition: transform 0.15s ease, background 0.15s ease;
}
.controls-panel button:hover {
    transform: translateY(-1px);
    background: #31436b;
}
.controls-panel button.active {
    background: #4a6cf0;
}
.breadcrumb {
    position: fixed;
    top: 64px;
    right: 16px;
    z-index: 9999;
    padding: 6px 10px;
    border-radius: 8px;
    background: rgba(15, 20, 30, 0.65);
    color: #fff;
    font-family: "Segoe UI", "Noto Sans TC", sans-serif;
    font-size: 12px;
    max-width: 320px;
}
.plotly-graph-div.clicked {
    filter: saturate(1.15);
}
.plotly-graph-div.clicked .sunburst path {
    stroke: rgba(255, 255, 255, 0.5);
    stroke-width: 1.5px;
}
"""

    return f"""
<style>
{selectors} {{
    transition: transform 0.25s ease, filter 0.25s ease;
    filter: drop-shadow(0 0 6px rgba(76, 130, 255, 0.6));
    transform: scale(1.03);
    transform-box: fill-box;
    transform-origin: center;
}}
.plotly .sunburst path,
.plotly .treemap path {{
    transition: transform 0.25s ease, filter 0.25s ease;
    transform-box: fill-box;
    transform-origin: center;
}}
{controls_css}
</style>
"""


def _build_js(chart_type: str) -> str:
    if chart_type != "sunburst":
        return ""

    return """
<script>
document.addEventListener("DOMContentLoaded", () => {
    const plotlyDiv = document.querySelector(".plotly-graph-div");
    if (!plotlyDiv || typeof Plotly === "undefined") {
        return;
    }

    const trace = plotlyDiv.data && plotlyDiv.data[0];
    if (!trace || !trace.ids || !trace.parents) {
        return;
    }

    const parentMap = new Map();
    const labelMap = new Map();
    const childrenMap = new Map();

    trace.ids.forEach((id, index) => {
        const parent = trace.parents[index];
        parentMap.set(id, parent);
        labelMap.set(id, trace.labels[index]);
        if (parent) {
            if (!childrenMap.has(parent)) {
                childrenMap.set(parent, []);
            }
            childrenMap.get(parent).push(id);
        }
    });

    const controls = document.createElement("div");
    controls.className = "controls-panel";
    controls.innerHTML = `
        <button data-action="reset">重置</button>
        <button data-action="back">返回</button>
        <button data-action="toggle">自動下鑽：開</button>
    `;
    document.body.appendChild(controls);

    const breadcrumb = document.createElement("div");
    breadcrumb.className = "breadcrumb";
    breadcrumb.textContent = "路徑：根";
    document.body.appendChild(breadcrumb);

    let autoDrill = true;
    let hoverTimer = null;
    const historyStack = [];

    const updateBreadcrumb = (id) => {
        if (!id) {
            breadcrumb.textContent = "路徑：根";
            return;
        }
        const path = [];
        let cursor = id;
        while (cursor) {
            path.unshift(labelMap.get(cursor) || cursor);
            cursor = parentMap.get(cursor);
        }
        breadcrumb.textContent = `路徑：${path.join(" / ")}`;
    };

    const drillTo = (id, pushHistory = true) => {
        if (!id) {
            Plotly.restyle(plotlyDiv, { level: [""] });
            updateBreadcrumb(null);
            return;
        }
        Plotly.restyle(plotlyDiv, { level: [id] });
        updateBreadcrumb(id);
        if (pushHistory) {
            historyStack.push(id);
        }
    };

    controls.addEventListener("click", (event) => {
        const target = event.target;
        if (!(target instanceof HTMLButtonElement)) {
            return;
        }
        const action = target.dataset.action;
        if (action === "reset") {
            historyStack.length = 0;
            drillTo(null, false);
        }
        if (action === "back") {
            historyStack.pop();
            const prev = historyStack[historyStack.length - 1] || null;
            drillTo(prev, false);
        }
        if (action === "toggle") {
            autoDrill = !autoDrill;
            target.classList.toggle("active", autoDrill);
            target.textContent = autoDrill ? "自動下鑽：開" : "自動下鑽：關";
        }
    });

    plotlyDiv.on("plotly_hover", (data) => {
        if (!autoDrill || !data || !data.points || !data.points[0]) {
            return;
        }
        const point = data.points[0];
        const pointId = point.id;
        updateBreadcrumb(pointId || null);
        if (!pointId || !childrenMap.has(pointId)) {
            return;
        }
        if (hoverTimer) {
            clearTimeout(hoverTimer);
        }
        hoverTimer = setTimeout(() => {
            drillTo(pointId, true);
            hoverTimer = null;
        }, 450);
    });

    plotlyDiv.on("plotly_unhover", () => {
        if (hoverTimer) {
            clearTimeout(hoverTimer);
            hoverTimer = null;
        }
    });

    plotlyDiv.on("plotly_click", (data) => {
        if (!data || !data.points || !data.points[0]) {
            return;
        }
        const pointId = data.points[0].id;
        if (pointId && childrenMap.has(pointId)) {
            drillTo(pointId, true);
        }
        plotlyDiv.classList.add("clicked");
        setTimeout(() => plotlyDiv.classList.remove("clicked"), 300);
    });
});
</script>
"""


def write_html_with_effects(
    fig: go.Figure,
    output_path: Path,
    chart_type: Optional[str] = None,
) -> None:
    html = fig.to_html(full_html=True, include_plotlyjs="cdn")
    css = _build_css(chart_type or "")
    js = _build_js(chart_type or "")
    injection = f"{css}{js}"

    if "</body>" in html:
        html = html.replace("</body>", f"{injection}</body>")
    else:
        html = f"{html}{injection}"

    output_path.write_text(html, encoding="utf-8")
