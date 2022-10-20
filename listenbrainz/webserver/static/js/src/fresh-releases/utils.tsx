export function formattedReleaseDate(releaseDate: string) {
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
  })
    .formatToParts(new Date(Date.parse(releaseDate)))
    .reverse()
    .map((date_parts) => date_parts.value)
    .join("");
}
