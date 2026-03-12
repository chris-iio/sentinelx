/**
 * SVG relationship graph renderer for the IOC detail page.
 *
 * Reads graph_nodes and graph_edges from data attributes on the
 * #relationship-graph container, then draws a hub-and-spoke SVG diagram
 * with the IOC at the center and provider nodes arranged in a circle around it.
 *
 * Nodes are colored by verdict to give instant visual triage context.
 *
 * SEC-08: All text content uses document.createTextNode() — never innerHTML
 * or textContent on elements with children. IOC values and provider names
 * are passed through createTextNode only to prevent XSS.
 */

interface GraphNode {
  id: string;
  label: string;
  verdict: string;
  role: "ioc" | "provider";
}

interface GraphEdge {
  from: string;
  to: string;
  verdict: string;
}

/** Verdict-to-fill-color mapping (matches CSS verdict variables). */
const VERDICT_COLORS: Record<string, string> = {
  malicious:  "#ef4444",
  suspicious: "#f97316",
  clean:      "#22c55e",
  known_good: "#3b82f6",
  no_data:    "#6b7280",
  error:      "#6b7280",
  ioc:        "#8b5cf6",
};

const SVG_NS = "http://www.w3.org/2000/svg";

function verdictColor(verdict: string): string {
  return VERDICT_COLORS[verdict] ?? "#6b7280";
}

/**
 * Create an SVG element in the SVG namespace.
 */
function svgEl(tag: string): SVGElement {
  return document.createElementNS(SVG_NS, tag) as SVGElement;
}

/**
 * Render the hub-and-spoke relationship graph into the given container.
 * Safe to call when no provider data is present — shows a fallback message.
 */
function renderRelationshipGraph(container: HTMLElement): void {
  const nodesAttr = container.getAttribute("data-graph-nodes");
  const edgesAttr = container.getAttribute("data-graph-edges");

  let nodes: GraphNode[] = [];
  let edges: GraphEdge[] = [];

  try {
    nodes = nodesAttr ? (JSON.parse(nodesAttr) as GraphNode[]) : [];
    edges = edgesAttr ? (JSON.parse(edgesAttr) as GraphEdge[]) : [];
  } catch {
    // Malformed JSON — show empty state
    nodes = [];
    edges = [];
  }

  const providerNodes = nodes.filter((n) => n.role === "provider");
  const iocNode = nodes.find((n) => n.role === "ioc");

  if (!iocNode || providerNodes.length === 0) {
    const msg = document.createElement("p");
    msg.className = "graph-empty";
    msg.appendChild(document.createTextNode("No provider data to graph"));
    container.appendChild(msg);
    return;
  }

  // ---- SVG canvas ----
  const svg = svgEl("svg");
  svg.setAttribute("viewBox", "0 0 600 400");
  svg.setAttribute("width", "100%");
  svg.setAttribute("role", "img");
  svg.setAttribute("aria-label", "Provider relationship graph");

  const cx = 300;  // center x
  const cy = 200;  // center y
  const orbitRadius = 150;
  const iocrr = 30;  // IOC node radius
  const prrr = 20;   // provider node radius

  // ---- Draw edges first (behind nodes) ----
  const edgeGroup = svgEl("g");
  edgeGroup.setAttribute("class", "graph-edges");

  for (const edge of edges) {
    const targetNode = providerNodes.find((n) => n.id === edge.to);
    if (!targetNode) continue;

    const idx = providerNodes.indexOf(targetNode);
    const angle = (2 * Math.PI * idx) / providerNodes.length - Math.PI / 2;
    const px = cx + orbitRadius * Math.cos(angle);
    const py = cy + orbitRadius * Math.sin(angle);

    const line = svgEl("line");
    line.setAttribute("x1", String(cx));
    line.setAttribute("y1", String(cy));
    line.setAttribute("x2", String(Math.round(px)));
    line.setAttribute("y2", String(Math.round(py)));
    line.setAttribute("stroke", verdictColor(edge.verdict));
    line.setAttribute("stroke-width", "2");
    line.setAttribute("opacity", "0.6");
    edgeGroup.appendChild(line);
  }

  svg.appendChild(edgeGroup);

  // ---- Draw provider nodes ----
  const nodeGroup = svgEl("g");
  nodeGroup.setAttribute("class", "graph-nodes");

  providerNodes.forEach((node, idx) => {
    const angle = (2 * Math.PI * idx) / providerNodes.length - Math.PI / 2;
    const px = cx + orbitRadius * Math.cos(angle);
    const py = cy + orbitRadius * Math.sin(angle);

    const group = svgEl("g");
    group.setAttribute("class", "graph-node graph-node--provider");

    // Accessible tooltip
    const title = svgEl("title");
    title.appendChild(document.createTextNode(node.id));
    group.appendChild(title);

    // Circle
    const circle = svgEl("circle");
    circle.setAttribute("cx", String(Math.round(px)));
    circle.setAttribute("cy", String(Math.round(py)));
    circle.setAttribute("r", String(prrr));
    circle.setAttribute("fill", verdictColor(node.verdict));
    group.appendChild(circle);

    // Label below circle (SEC-08: createTextNode)
    const text = svgEl("text");
    text.setAttribute("x", String(Math.round(px)));
    text.setAttribute("y", String(Math.round(py + prrr + 14)));
    text.setAttribute("text-anchor", "middle");
    text.setAttribute("font-size", "11");
    text.setAttribute("fill", "#e5e7eb");
    text.appendChild(document.createTextNode(node.label.slice(0, 12)));
    group.appendChild(text);

    nodeGroup.appendChild(group);
  });

  svg.appendChild(nodeGroup);

  // ---- Draw IOC center node (on top) ----
  const iocGroup = svgEl("g");
  iocGroup.setAttribute("class", "graph-node graph-node--ioc");

  const iocTitle = svgEl("title");
  iocTitle.appendChild(document.createTextNode(iocNode.id));
  iocGroup.appendChild(iocTitle);

  const iocCircle = svgEl("circle");
  iocCircle.setAttribute("cx", String(cx));
  iocCircle.setAttribute("cy", String(cy));
  iocCircle.setAttribute("r", String(iocrr));
  iocCircle.setAttribute("fill", verdictColor("ioc"));
  iocGroup.appendChild(iocCircle);

  const iocText = svgEl("text");
  iocText.setAttribute("x", String(cx));
  iocText.setAttribute("y", String(cy + 4));
  iocText.setAttribute("text-anchor", "middle");
  iocText.setAttribute("font-size", "10");
  iocText.setAttribute("fill", "#fff");
  iocText.setAttribute("font-weight", "bold");
  iocText.appendChild(document.createTextNode(iocNode.label.slice(0, 20)));
  iocGroup.appendChild(iocText);

  svg.appendChild(iocGroup);

  container.appendChild(svg);
}

/**
 * Initialize the graph module.
 * Finds the #relationship-graph element and renders the SVG if present.
 */
export function init(): void {
  const container = document.getElementById("relationship-graph");
  if (container) {
    renderRelationshipGraph(container);
  }
}
