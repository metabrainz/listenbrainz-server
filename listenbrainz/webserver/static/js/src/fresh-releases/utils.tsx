const formattedReleaseDate = (releaseDate: string) => {
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
  })
    .formatToParts(new Date(Date.parse(releaseDate)))
    .reverse()
    .map((date_parts) => date_parts.value)
    .join("");
};

/* All credits to Joackim Pennerup for coming up with
 * a framework/library agnostic solution for this.
 *
 * https://stackoverflow.com/a/72299932/4458075
 *
 */
function showTooltipOnOverflow() {
  let lastMouseOverElement: Element | null = null;
  document.addEventListener("mouseover", function (event) {
    const element = event.target;
    if (element instanceof Element && element != lastMouseOverElement) {
      lastMouseOverElement = element;
      const style = window.getComputedStyle(element);
      const whiteSpace = style.getPropertyValue("white-space");
      const textOverflow = style.getPropertyValue("text-overflow");
      if (
        whiteSpace == "nowrap" &&
        textOverflow == "ellipsis" &&
        element.offsetWidth < element.scrollWidth
      ) {
        element.setAttribute("title", element.textContent);
      } else {
        element.removeAttribute("title");
      }
    }
  });
}

// eslint-disable-next-line import/prefer-default-export
export { formattedReleaseDate, showTooltipOnOverflow };
