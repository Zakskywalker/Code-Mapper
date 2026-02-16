class GraphRenderer {
  constructor(root) {
    this.root = root;
    this.points = [];
  }

  push(point) {
    this.points.push(point);
    this.render();
  }

  render() {
    this.root.innerHTML = this.points.map(p => `<div class="badge">${p.label}: ${p.value}</div>`).join("");
  }
}

const summary = document.getElementById("summary");
const status = document.getElementById("status");
const renderer = new GraphRenderer(summary);

window.bus.on("metric", (m) => renderer.push(m));
status.textContent = "Ready";
window.bus.emit("metric", { label: "events", value: 42 });
