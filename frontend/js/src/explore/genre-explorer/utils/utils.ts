import tinycolor from "tinycolor2";

// eslint-disable-next-line import/prefer-default-export
export function transformGenreData(data: GenreExplorerLoaderData) {
  if (!data) return { nodes: [], links: [] };

  const mainNodeSize = 150;
  const childNodeSize = 85;
  const mainColor = "#353070";

  const nodes = [
    // Main genre node
    {
      id: data.genre.id,
      name: data.genre.name,
      size: mainNodeSize,
      color: mainColor,
    },
    // Child genre nodes
    ...data.children.map((child) => ({
      id: child.id,
      name: child.name,
      size: childNodeSize,
      color: tinycolor(mainColor).lighten(30).toString(),
    })),
    // Parent genre nodes with different color
    ...data.parents.nodes.map((parent) => ({
      id: parent.id,
      name: parent.name,
      size: childNodeSize,
      color: tinycolor(mainColor).darken(15).toString(),
    })),
  ];

  // Remove duplicate nodes
  const uniqueNodes = nodes.filter(
    (node, index, self) => index === self.findIndex((t) => t.id === node.id)
  );

  // Create links
  const links = [
    // Links to children
    ...data.children.map((child) => ({
      source: data.genre.id,
      target: child.id,
    })),
    // Links to parents
    ...data.parents.edges,
  ];

  return { nodes: uniqueNodes, links };
}
