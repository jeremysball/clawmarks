const title = document.getElementById("field-title");
const event = document.getElementById("field-event");
const anchor = document.querySelector(".anchor");

anchor.dataset.label = title.textContent.toUpperCase();

document.querySelectorAll("#field-grid .tile").forEach((tile) => {
  tile.addEventListener("click", () => {
    document.querySelectorAll("#field-grid .tile").forEach((item) => item.classList.remove("selected"));
    tile.classList.add("selected");
    title.textContent = tile.dataset.name;
    anchor.dataset.label = tile.dataset.name.toUpperCase();
    event.textContent = `Selected ${tile.dataset.name}. The real inspector loads its image, original-space neighbors, rating history, and lineage.`;
  });
});

document.querySelectorAll("[data-action]").forEach((button) => {
  button.addEventListener("click", () => {
    const messages = {
      review: "Review queue opened in the production flow. It selects an uncertain but visually informative pair from this neighborhood.",
      batch: "Batch preflight opened in the production flow. It records this anchor, the allowed controls, and the cost ceiling before submission.",
      probe: "Anchor marked for the later text-conditioning probe. That experiment remains separate from this first visual release.",
    };
    event.textContent = messages[button.dataset.action];
  });
});
