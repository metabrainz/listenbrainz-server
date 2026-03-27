// src/LinkListens.tsx (versión mínima para sandbox)
import React from "react";
import { groupBy, pick, size, sortBy } from "lodash";

// --- Mocks para componentes que no existen en el sandbox ---
const Loader = () => <div>Loading...</div>;
const ListenCard = ({ track }: any) => (
  <div>{track.track_metadata.track_name}</div>
);
const ListenControl = () => <div></div>;
const MBIDMappingModal = () => <div></div>;
const MultiTrackMBIDMappingModal = () => <div></div>;
const Accordion = ({ children }: any) => <div>{children}</div>;
const Pagination = () => <div></div>;

// --- Tipos simplificados ---
export interface Track {
  recording_msid: string;
  track_metadata: {
    track_name: string;
    artist_name: string;
    release_name: string;
  };
}

type LinkListensProps = {
  listens: Track[];
};

const EXPECTED_ITEMS_PER_PAGE = 25;

export default function LinkListens({ listens }: LinkListensProps) {
  // --- Estado inicial con tu fix ---
  const [sortedUnlinkedListensGroups, setSortedUnlinkedListensGroups] =
    React.useState(() => {
      const grouped = groupBy(listens, "track_metadata.release_name");

      const noReleaseNameGroup = pick(grouped, "null");
      if (size(noReleaseNameGroup) > 0) delete grouped.null;

      const sortedGroups = sortBy(grouped, (g) => g.length).reverse();

      if (noReleaseNameGroup.null?.length) sortedGroups.push(noReleaseNameGroup.null);

      return sortedGroups;
    });

  const [searchQuery, setSearchQuery] = React.useState("");

  // --- Búsqueda simple ---
  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmedQuery = searchQuery.trim().toLowerCase();
    if (!trimmedQuery) {
      // Reset
      setSortedUnlinkedListensGroups(() =>
        sortBy(groupBy(listens, "track_metadata.release_name"), (g) => g.length).reverse()
      );
      return;
    }
    const filtered = listens.filter((track) =>
      track.track_metadata.track_name.toLowerCase().includes(trimmedQuery)
    );
    const grouped = groupBy(filtered, "track_metadata.release_name");
    setSortedUnlinkedListensGroups(sortBy(grouped, (g) => g.length).reverse());
  };

  return (
    <div>
      <h2>Total listens: {listens.length}</h2>

      <form onSubmit={handleSearch}>
        <input
          type="text"
          placeholder="Search track..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />
        <button type="submit">Search</button>
      </form>

      <div>
        {sortedUnlinkedListensGroups.map((group, idx) => (
          <Accordion key={idx}>
            {group.map((track) => (
              <ListenCard key={track.recording_msid} track={track} />
            ))}
          </Accordion>
        ))}
      </div>

      <Pagination />
    </div>
  );
}