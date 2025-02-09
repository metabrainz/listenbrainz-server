import * as React from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Helmet } from "react-helmet";
import tinycolor from "tinycolor2";
import { kebabCase } from "lodash";
import { toast } from "react-toastify";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faCopy, faDownload } from "@fortawesome/free-solid-svg-icons";
import { RouteQuery } from "../../utils/Loader";
import {
  copyImageToClipboard,
  downloadComponentAsImage,
} from "../music-neighborhood/utils/utils";
import { ToastMsg } from "../../notifications/Notifications";
import GenreGraph from "./components/GenreGraph";
import Panel from "./components/Panel";
import SearchBox from "./components/SearchBox";

type GenreExplorerParams = {
  genreMBID: string;
};

type GenreNode = {
  id: string;
  name: string;
};

type GenreExplorerLoaderData = {
  children: GenreNode[];
  parents: {
    nodes: GenreNode[];
    edges: {
      source: string;
      target: string;
    }[];
  };
  siblings: GenreNode[];
  genre: GenreNode;
};

function transformGenreData(data: GenreExplorerLoaderData) {
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

export default function GenreExplorer() {
  const location = useLocation();
  const navigate = useNavigate();
  const { genreMBID } = useParams<GenreExplorerParams>();
  const graphParentElementRef = React.useRef<HTMLDivElement>(null);

  const { data } = useQuery<GenreExplorerLoaderData>(
    RouteQuery(["genre-explorer"], location.pathname)
  );

  const graphData = React.useMemo(() => transformGenreData(data!), [data]);

  const handleGenreChange = (newGenreMBID: string) => {
    navigate(`/explore/genre-explorer/${newGenreMBID}`);
  };

  const onClickDownload = React.useCallback(async () => {
    if (!graphParentElementRef?.current) {
      return;
    }

    try {
      downloadComponentAsImage(
        graphParentElementRef.current,
        `${kebabCase(data?.genre.name)}-genre-explorer.png`
      );
    } catch (error) {
      toast.error(
        <ToastMsg
          title="Could not save as an image"
          message={typeof error === "object" ? error.message : error.toString()}
        />,
        { toastId: "download-svg-error" }
      );
    }
  }, [data, graphParentElementRef]);

  const copyImage = React.useCallback(async () => {
    if (!graphParentElementRef?.current) {
      return;
    }

    await copyImageToClipboard(graphParentElementRef.current);
  }, [graphParentElementRef]);

  const browserHasClipboardAPI = "clipboard" in navigator;

  return (
    <>
      <Helmet>
        <title>Genre Explorer</title>
      </Helmet>
      <div className="genre-explorer-main-container" role="main">
        <div className="genre-explorer-header">
          <SearchBox onGenreSelect={handleGenreChange} />
          <div className="share-buttons">
            <button
              type="button"
              className="btn btn-icon btn-info"
              onClick={onClickDownload}
            >
              <FontAwesomeIcon icon={faDownload} color="white" />
            </button>
            {browserHasClipboardAPI && (
              <button
                type="button"
                className="btn btn-icon btn-info"
                onClick={copyImage}
              >
                <FontAwesomeIcon icon={faCopy} color="white" />
              </button>
            )}
          </div>
        </div>
        <div className="genre-explorer-content">
          <GenreGraph
            data={graphData}
            onGenreChange={handleGenreChange}
            graphParentElementRef={graphParentElementRef}
          />
          <Panel genre={data?.genre ?? null} />
        </div>
      </div>
    </>
  );
}
