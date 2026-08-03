const base = "http://100.69.206.107:8451/notes/uncanny_sweep/thumbs/";

const neighborhoods = {
  cat: {
    label: "Cat studies",
    anchorTag: "grid_s0.6_c2.0_style_cat_seed11",
    anchorId: "GRID S0.6 / C2.0 / CAT / 11",
    anchorDesc: "trentbuckle style, close-up cat portrait · seed 11 · fixed sweep · no rating",
    neighbors: [
      ["grid_s1.0_c2.0_style_cat_seed11", 0.8918, "unrated"],
      ["grid_s1.4_c5.0_style_cat_seed11", 0.7911, "yes"],
      ["grid_s1.0_c2.0_style_wolf_seed11", 0.7516, "no"],
      ["grid_s1.4_c7.5_style_cat_seed11", 0.7331, "unrated"],
      ["grid_s1.0_c2.0_style_fox_seed11", 0.7244, "unrated"],
      ["grid_s1.4_c7.5_style_fox_seed11", 0.7237, "yes"],
      ["grid_s0.6_c2.0_style_fox_seed11", 0.7221, "unrated"],
      ["grid_s1.8_c7.5_style_cat_seed11", 0.7033, "unrated"],
    ],
  },
  animal: {
    label: "Animal drift",
    anchorTag: "grid_s1.0_c2.0_style_wolf_seed11",
    anchorId: "GRID S1.0 / C2.0 / WOLF / 11",
    anchorDesc: "trentbuckle style, wolf portrait, moderate strength · seed 11 · fixed sweep · no rating",
    neighbors: [
      ["grid_s1.0_c2.0_style_fox_seed11", 0.8452, "unrated"],
      ["grid_s0.6_c2.0_style_wolf_seed22", 0.8107, "yes"],
      ["grid_s1.0_c5.0_style_wolf_seed11", 0.7893, "unrated"],
      ["grid_s1.0_c2.0_style_owl_seed11", 0.7402, "no"],
      ["grid_s1.4_c2.0_style_wolf_seed11", 0.7288, "unrated"],
      ["grid_s0.6_c5.0_style_fox_seed22", 0.7190, "unrated"],
      ["grid_s1.0_c7.5_style_wolf_seed22", 0.7052, "yes"],
      ["grid_s1.4_c5.0_style_fox_seed11", 0.6981, "unrated"],
    ],
  },
  fox: {
    label: "Fox variants",
    anchorTag: "grid_s1.0_c2.0_style_fox_seed11",
    anchorId: "GRID S1.0 / C2.0 / FOX / 11",
    anchorDesc: "trentbuckle style, fox portrait · seed 11 · fixed sweep · no rating",
    neighbors: [
      ["grid_s0.6_c2.0_style_fox_seed11", 0.8709, "yes"],
      ["grid_s1.4_c2.0_style_fox_seed22", 0.8033, "unrated"],
      ["grid_s1.0_c5.0_style_fox_seed11", 0.7820, "unrated"],
      ["grid_s1.0_c2.0_style_wolf_seed22", 0.7455, "no"],
      ["grid_s1.0_c7.5_style_fox_seed22", 0.7301, "unrated"],
      ["grid_s0.6_c7.5_style_fox_seed11", 0.7256, "unrated"],
      ["grid_s1.4_c7.5_style_fox_seed11", 0.7180, "yes"],
      ["grid_s1.0_c12.0_style_fox_seed11", 0.6874, "unrated"],
    ],
  },
  overdrive: {
    label: "Overdriven marks",
    anchorTag: "grid_s1.4_c7.5_style_cat_seed11",
    anchorId: "GRID S1.4 / C7.5 / CAT / 11",
    anchorDesc: "trentbuckle style, overdriven LoRA strength · seed 11 · fixed sweep · no rating",
    neighbors: [
      ["grid_s1.8_c7.5_style_cat_seed11", 0.8221, "unrated"],
      ["grid_s1.4_c12.0_style_cat_seed11", 0.8017, "no"],
      ["grid_s1.4_c7.5_style_fox_seed11", 0.7699, "unrated"],
      ["grid_s1.8_c12.0_style_cat_seed22", 0.7488, "yes"],
      ["grid_s1.4_c5.0_style_cat_seed22", 0.7305, "unrated"],
      ["grid_s1.0_c7.5_style_cat_seed11", 0.7166, "unrated"],
      ["grid_s1.4_c7.5_style_wolf_seed11", 0.7002, "no"],
      ["grid_s1.8_c7.5_style_fox_seed11", 0.6844, "unrated"],
    ],
  },
};

let activeId = "cat";
let selected = 0;
let filter = "all";
const flagged = {}; // "cat:2" -> true
const eventLog = [];

const indexNav = document.getElementById("index");
const activeTitle = document.getElementById("active-title");
const anchorImage = document.getElementById("anchor-image");
const anchorId = document.getElementById("anchor-id");
const anchorDesc = document.getElementById("anchor-desc");
const grid = document.getElementById("neighbors");
const inspectImage = document.getElementById("inspect-image");
const inspectTitle = document.getElementById("inspect-title");
const inspectSim = document.getElementById("inspect-sim");
const inspectPrompt = document.getElementById("inspect-prompt");
const inspectSeed = document.getElementById("inspect-seed");
const event = document.getElementById("lt-event");
const filtersBar = document.getElementById("filters");
const makeAnchorBtn = document.getElementById("make-anchor");
const probeBtn = document.getElementById("probe-btn");

function tagMeta(tag) {
  const m = tag.match(/style_(\w+)_seed(\d+)/);
  return { prompt: m ? `${m[1]} portrait` : "unknown", seed: m ? m[2] : "?" };
}

function flagKey(index) {
  return `${activeId}:${index}`;
}

function log(text) {
  eventLog.unshift(`${new Date().toLocaleTimeString()} — ${text}`);
  event.textContent = text;
}

function currentNeighborhood() {
  return neighborhoods[activeId];
}

function passesFilter(state) {
  if (filter === "all") return true;
  if (filter === "unrated") return state === "unrated";
  if (filter === "preferred") return state === "yes";
  return true;
}

function renderNeighborhoodNav() {
  document.querySelectorAll(".neighborhood").forEach((button) => {
    button.classList.toggle("active", button.dataset.id === activeId);
  });
}

function renderAnchor() {
  const n = currentNeighborhood();
  anchorImage.src = `${base}${n.anchorTag}.jpg`;
  anchorId.textContent = n.anchorId;
  anchorDesc.textContent = n.anchorDesc;
  activeTitle.textContent = n.label;
}

function renderNeighbors() {
  const n = currentNeighborhood();
  grid.innerHTML = n.neighbors.map(([tag, similarity, state], index) => {
    const hidden = passesFilter(state) ? "" : " hidden";
    const isFlagged = flagged[flagKey(index)];
    return `
    <button class="neighbor ${index === selected ? "selected" : ""}${hidden}" data-index="${index}">
      <img src="${base}${tag}.jpg"><span class="rank">#${index + 1}</span>
      ${isFlagged ? '<span class="flag">P</span>' : ""}
      <span class="ncap"><span>${similarity.toFixed(4)}</span><span class="${state}">${state}</span></span>
    </button>`;
  }).join("");
  document.querySelectorAll(".neighbor").forEach((button) => button.addEventListener("click", () => selectNeighbor(Number(button.dataset.index))));
}

function renderInspector() {
  const n = currentNeighborhood();
  const [tag, similarity, state] = n.neighbors[selected];
  const meta = tagMeta(tag);
  inspectImage.src = `${base}${tag}.jpg`;
  inspectTitle.textContent = `Rank ${selected + 1}`;
  inspectSim.textContent = similarity.toFixed(4);
  inspectPrompt.textContent = meta.prompt;
  inspectSeed.textContent = meta.seed;
  const buttons = { yes: document.getElementById("yes"), no: document.getElementById("no") };
  Object.entries(buttons).forEach(([name, button]) => {
    button.classList.toggle("active", name === state);
    button.classList.toggle(name === "yes" ? "y" : "n", name === state);
  });
  makeAnchorBtn.disabled = false;
  probeBtn.classList.toggle("flagged", !!flagged[flagKey(selected)]);
  probeBtn.textContent = flagged[flagKey(selected)] ? "Remove from text-response probe" : "Add to text-response probe";
}

function renderAll() {
  renderNeighborhoodNav();
  renderAnchor();
  renderNeighbors();
  renderInspector();
}

function selectNeighborhood(id) {
  activeId = id;
  selected = 0;
  log(`Switched to ${neighborhoods[id].label}. Anchor and neighbor ranking now reflect this neighborhood.`);
  renderAll();
}

function selectNeighbor(index) {
  selected = index;
  renderNeighbors();
  renderInspector();
  log(`Inspecting neighbor ${index + 1}. The anchor remains fixed until you choose Make anchor.`);
}

function setRating(label) {
  const n = currentNeighborhood();
  n.neighbors[selected][2] = label;
  renderNeighbors();
  renderInspector();
  log(`Recorded ${label} for ranked neighbor ${selected + 1} in ${n.label}.`);
}

function setFilter(name) {
  filter = name;
  document.querySelectorAll(".filters button").forEach((b) => b.classList.toggle("active", b.dataset.filter === name));
  const visible = currentNeighborhood().neighbors.filter(([, , state]) => passesFilter(state)).length;
  if (!passesFilter(currentNeighborhood().neighbors[selected][2]) && visible > 0) {
    selected = currentNeighborhood().neighbors.findIndex(([, , state]) => passesFilter(state));
  }
  renderNeighbors();
  renderInspector();
  log(`Filter set to ${name}. ${visible} of ${currentNeighborhood().neighbors.length} neighbors shown.`);
}

function makeAnchor() {
  const n = currentNeighborhood();
  const promotedRank = selected + 1;
  const [tag, , state] = n.neighbors[selected];
  const meta = tagMeta(tag);
  const oldAnchorTag = n.anchorTag;
  n.anchorTag = tag;
  n.anchorId = `GRID / ${meta.prompt.toUpperCase()} / ${meta.seed}`;
  n.anchorDesc = `trentbuckle style, ${meta.prompt} · seed ${meta.seed} · fixed sweep · ${state} rating`;
  n.neighbors[selected] = [oldAnchorTag, 1.0, "unrated"];
  selected = 0;
  renderAll();
  log(`Made rank ${promotedRank} the new anchor for ${n.label}. Previous anchor moved into the neighbor list for re-ranking.`);
}

function toggleProbe() {
  const key = flagKey(selected);
  flagged[key] = !flagged[key];
  renderNeighbors();
  renderInspector();
  log(flagged[key] ? `Flagged rank ${selected + 1} for the future text-response probe.` : `Removed rank ${selected + 1} from the text-response probe list.`);
}

function compareWithAnchor() {
  const n = currentNeighborhood();
  const [, similarity] = n.neighbors[selected];
  log(`Comparing rank ${selected + 1} (similarity ${similarity.toFixed(4)}) against anchor ${n.anchorId}. Full compare view is a later feature; this prototype only records the intent.`);
}

function renderLog() {
  const body = document.getElementById("logbody");
  body.innerHTML = eventLog.length
    ? eventLog.map((line) => `<div class="logline">${line}</div>`).join("")
    : '<div class="logline">No actions recorded yet.</div>';
}

document.querySelectorAll(".neighborhood").forEach((button) => button.addEventListener("click", () => selectNeighborhood(button.dataset.id)));
document.querySelectorAll(".filters button").forEach((button) => button.addEventListener("click", () => setFilter(button.dataset.filter)));
document.getElementById("yes").addEventListener("click", () => setRating("yes"));
document.getElementById("no").addEventListener("click", () => setRating("no"));
makeAnchorBtn.addEventListener("click", makeAnchor);
probeBtn.addEventListener("click", toggleProbe);
document.getElementById("compare-btn").addEventListener("click", compareWithAnchor);
document.getElementById("prepare").addEventListener("click", () => document.getElementById("sheet").classList.add("open"));
document.getElementById("cancel").addEventListener("click", () => document.getElementById("sheet").classList.remove("open"));
document.getElementById("launch").addEventListener("click", () => {
  document.getElementById("sheet").classList.remove("open");
  log("Demo confirmation recorded. The production action would submit the persisted batch plan here.");
});
document.getElementById("explog").addEventListener("click", () => {
  renderLog();
  document.getElementById("logsheet").classList.add("open");
});
document.getElementById("closelog").addEventListener("click", () => document.getElementById("logsheet").classList.remove("open"));
document.getElementById("method-link").addEventListener("click", () => log("Method note: centroid/nearest-neighbor DINOv2 similarity, see lab_notebook.md Section 2."));
document.getElementById("overview-link").addEventListener("click", () => log("2D overview is a navigation view only; it does not claim to preserve original embedding-space geometry."));

document.addEventListener("keydown", (e) => {
  if (e.key === "y" || e.key === "Y") setRating("yes");
  if (e.key === "n" || e.key === "N") setRating("no");
});

log("Select a neighbor, then record your judgment.");
renderAll();
