import * as React from "react";

export default function getEntityLink(
  entityType: Entity,
  entityName: string,
  entityMBID?: string
): JSX.Element {
  if (entityMBID) {
    return (
      <a
        className="underlined-link"
        href={`https://musicbrainz.org/${entityType}/${entityMBID}`}
        target="_blank"
        rel="noopener noreferrer"
      >
        {entityName}
      </a>
    );
  }
  return <>{entityName}</>;
}
