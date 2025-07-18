import * as React from "react";
import { faInfo } from "@fortawesome/free-solid-svg-icons";
import { useQuery } from "@tanstack/react-query";
import Spinner from "react-loader-spinner";
import { Link } from "react-router";
import SideBar from "../../../components/Sidebar";
import { COLOR_LB_ORANGE } from "../../../utils/constants";
import GlobalAppContext from "../../../utils/GlobalAppContext";

type GenreWithWiki = {
  id: string;
  name: string;
  wiki_extract?: string;
};

type PanelProps = {
  genre: GenreWithWiki | null;
};

function Panel({ genre }: PanelProps) {
  const { APIService } = React.useContext(GlobalAppContext);
  const { data: wikiData, isLoading } = useQuery({
    queryKey: ["genre-wiki", genre?.id],
    queryFn: async () => {
      if (!genre?.id) return null;
      return APIService.getGenreWikipediaExtract(genre.id);
    },
  });

  if (!genre) {
    return null;
  }

  return (
    <SideBar toggleIcon={faInfo}>
      {isLoading ? (
        <div className="spinner-container">
          <Spinner
            type="ThreeDots"
            color={COLOR_LB_ORANGE}
            height={100}
            width={100}
            visible
          />
          <div
            className="text-muted"
            style={{ fontSize: "2rem", margin: "1rem" }}
          >
            Loading&#8230;
          </div>
        </div>
      ) : (
        <>
          <div className="sidebar-header">
            <p id="genre-name">{genre.name}</p>
          </div>
          <div className="genre-panel-info">
            <div id="genre-wiki">{wikiData}</div>
            <div className="genre-mb-link">
              <Link
                id="genre-mb-link-button"
                target="_blank"
                rel="noopener noreferrer"
                to={`https://musicbrainz.org/genre/${genre.id}`}
              >
                <strong>Genre page</strong>
              </Link>
            </div>
          </div>
        </>
      )}
    </SideBar>
  );
}

export default Panel;
