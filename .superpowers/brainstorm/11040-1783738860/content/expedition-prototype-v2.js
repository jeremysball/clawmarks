const root = document.getElementById("expedition");

document.querySelectorAll(".theme button").forEach((button) => {
  button.addEventListener("click", () => {
    root.dataset.theme = button.dataset.theme;
    document.querySelectorAll(".theme button").forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
  });
});

function showPane(name) {
  document.querySelectorAll(".tabs button").forEach((button) => {
    button.classList.toggle("active", button.dataset.pane === name);
  });
  document.querySelectorAll(".pane").forEach((pane) => {
    pane.classList.toggle("active", pane.id === name);
  });
}

document.querySelectorAll(".tabs button").forEach((button) => {
  button.addEventListener("click", () => showPane(button.dataset.pane));
});

document.querySelectorAll(".tile").forEach((tile) => {
  tile.addEventListener("click", () => {
    document.querySelectorAll(".tile").forEach((item) => item.classList.remove("selected"));
    tile.classList.add("selected");
    document.getElementById("anchor-title").textContent = tile.dataset.anchor;
    document.getElementById("atlas-notice").textContent =
      `Selected ${tile.dataset.anchor}. The real inspector loads its original-space neighbors, ratings, and lineage.`;
  });
});

document.querySelectorAll("[data-go]").forEach((button) => {
  button.addEventListener("click", () => showPane(button.dataset.go));
});

document.querySelectorAll("[data-notice]").forEach((button) => {
  button.addEventListener("click", () => {
    document.getElementById("atlas-notice").textContent = button.dataset.notice;
  });
});

document.querySelectorAll("[data-vote]").forEach((button) => {
  button.addEventListener("click", () => {
    document.getElementById("review-notice").textContent =
      `Recorded ${button.dataset.vote} in the prototype. The real queue saves the judgment and requests the next useful pair.`;
  });
});

function updateBatch() {
  const batch = Number(document.getElementById("batch").value);
  const share = Number(document.getElementById("share").value) / 100;
  const audit = Math.max(2, Math.round(batch * 0.1));
  const explore = Math.round((batch - audit) * share);
  const exploit = batch - audit - explore;
  const cost = (batch * 0.021).toFixed(2);
  document.getElementById("batch-label").textContent = `${batch} images`;
  document.getElementById("share-label").textContent = `${Math.round(share * 100)}%`;
  document.getElementById("explore-count").textContent = explore;
  document.getElementById("exploit-count").textContent = exploit;
  document.getElementById("audit-count").textContent = audit;
  document.getElementById("budget").textContent = `$${cost} maximum`;
  document.getElementById("confirm-title").textContent = `Launch ${batch} images for up to $${cost}?`;
}

document.getElementById("batch").addEventListener("input", updateBatch);
document.getElementById("share").addEventListener("input", updateBatch);

document.getElementById("open-confirm").addEventListener("click", () => {
  document.getElementById("modal").classList.add("open");
});
document.getElementById("cancel").addEventListener("click", () => {
  document.getElementById("modal").classList.remove("open");
});
document.getElementById("confirm").addEventListener("click", () => {
  document.getElementById("modal").classList.remove("open");
  document.getElementById("status").textContent = "DEMO CONFIRMED";
  document.getElementById("run-notice").textContent =
    "Demo confirmation recorded. Production would submit the persisted batch plan here.";
});
