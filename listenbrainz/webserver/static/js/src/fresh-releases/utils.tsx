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

// eslint-disable-next-line import/prefer-default-export
export { formattedReleaseDate };
