// Provide consistent arrow-key access to horizontally scrollable table regions.
document.addEventListener("keydown", function (event) {
  const region = event.target;
  if (
    event.defaultPrevented || event.altKey || event.ctrlKey || event.metaKey || event.shiftKey ||
    !region.matches || !region.matches(".table-responsive[tabindex]") ||
    region.scrollWidth <= region.clientWidth
  ) {
    return;
  }
  if (event.key === "ArrowLeft" || event.key === "ArrowRight") {
    const direction = event.key === "ArrowRight" ? 1 : -1;
    region.scrollBy({left: direction * Math.max(80, region.clientWidth * 0.8), behavior: "auto"});
    event.preventDefault();
  }
});
