import * as React from "react";

export default function DropdownRef() {
  // Ref
  const ref = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    document.addEventListener("keydown", (event: KeyboardEvent) => {
      const divElement = ref.current!;
      if (!divElement) {
        return;
      }
      const dropdown = ref.current?.querySelector("select");
      if (!dropdown) {
        return;
      }

      // First check if the event is coming from the dropdown or inside the dropdown
      if (
        dropdown &&
        (event.target === dropdown || divElement.contains(event.target as Node))
      ) {
        const selectedOption = dropdown.options[dropdown.selectedIndex];
        if (event.key === "ArrowDown") {
          event.preventDefault();
          const nextOption = dropdown.options[dropdown.selectedIndex + 1];
          if (nextOption) {
            if (selectedOption) {
              selectedOption.style.backgroundColor = "white";
              selectedOption.style.color = "inherit";
            }

            nextOption.style.backgroundColor = "#353070";
            nextOption.style.color = "#ffffff";

            nextOption.selected = true;
          }
          nextOption.scrollIntoView({
            block: "nearest",
          });
        } else if (event.key === "ArrowUp") {
          event.preventDefault();
          const prevOption = dropdown.options[dropdown.selectedIndex - 1];
          if (prevOption) {
            if (selectedOption) {
              selectedOption.style.backgroundColor = "white";
              selectedOption.style.color = "inherit";
            }

            prevOption.style.backgroundColor = "#353070";
            prevOption.style.color = "#ffffff";

            prevOption.selected = true;
          }
          prevOption.scrollIntoView({
            block: "nearest",
          });
        } else if (event.key === "Enter") {
          event.preventDefault();
          if (selectedOption) {
            const changeEvent = new Event("change", { bubbles: true });
            dropdown.dispatchEvent(changeEvent);

            (document?.activeElement as HTMLInputElement)?.blur();
          }
        }
      }
    });
  }, []);

  return ref;
}
