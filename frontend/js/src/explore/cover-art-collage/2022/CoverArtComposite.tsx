import React, { useCallback, useEffect, useRef, useState } from "react";
import panzoom, { PanZoom } from "panzoom";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faHandPointRight, faSyncAlt } from "@fortawesome/free-solid-svg-icons";
import jsonMap from "./data/rainbow1-100-7.json";
import SEO, { CACYearStyleTags } from "../SEO";

type CoverDef = {
  x1: number;
  x2: number;
  y1: number;
  y2: number;
  name: string;
  release_mbid: string;
};

export default function CoverArtComposite() {
  const targetRef = useRef<HTMLImageElement>(null);
  const [preventClick, setPreventClick] = useState(false);
  const [bigImageActive, setBigImageActive] = useState(false);
  const [panZoomInstance, setPanZoomInstance] = useState<PanZoom>();

  const setInitialZoom = useCallback(() => {
    if (!panZoomInstance) {
      return;
    }
    panZoomInstance.moveTo(0, 0);
    panZoomInstance.smoothZoom(
      0, // initial x position
      0, // initial y position
      panZoomInstance.getMinZoom() // initial zoom
    );
  }, [panZoomInstance]);

  useEffect(() => {
    if (!targetRef.current || !bigImageActive) return;

    const container = targetRef.current.parentElement as HTMLDivElement;
    const containerWidth = container.clientWidth;
    const imageWidth = 10000;
    const lowestZoom = containerWidth / imageWidth;
    const createdPanZoomInstance = panzoom(targetRef.current, {
      maxZoom: 1,
      minZoom: lowestZoom,
      bounds: true,
      onTouch: () => false, // how to allow touch events to work on mobile. See https://github.com/anvaka/panzoom/issues/235#issuecomment-1207341563
    });
    createdPanZoomInstance.smoothZoomAbs(0, 0, lowestZoom);
    setPanZoomInstance(createdPanZoomInstance);
    /* Prevent clicks while panning */
    createdPanZoomInstance.on("panstart", (e) => {
      setPreventClick(true);
    });
    createdPanZoomInstance.on("panend", (e) => {
      setTimeout(() => {
        setPreventClick(false);
      }, 100);
    });
  }, [bigImageActive]);

  return (
    <div
      id="year-in-music"
      className="yim-2022"
      style={{
        textAlign: "center",
        backgroundColor: "#ff0e25",
        color: "#ffcc49",
        WebkitOverflowScrolling: "auto", // See https://github.com/anvaka/panzoom/issues/235#issuecomment-1207341563
      }}
    >
      <SEO year={2022} />
      <CACYearStyleTags year={2022} />
      <div className="red-section">
        <div
          className="header"
          style={{ marginBottom: "0.5em", height: "15vh" }}
        >
          Album covers of 2022
          <div className="subheader">
            Zoom, drag and click your way to some of last years most colourful
            albums.
          </div>
        </div>
        {bigImageActive && (
          <button
            type="button"
            className="btn"
            onClick={setInitialZoom}
            style={{
              color: "#ff0e25",
              backgroundColor: "#ffcc49",
            }}
          >
            <FontAwesomeIcon icon={faSyncAlt} /> Reset
          </button>
        )}
        <div
          style={{
            width: "100%",
            height: "70vh",
            overflow: "hidden",
            position: "relative",
          }}
        >
          {!bigImageActive ? (
            <>
              <div
                className="flex flex-center"
                style={{ width: "100%", top: "10em", position: "absolute" }}
              >
                <div
                  className="alert alert-warning"
                  style={{ maxWidth: "700px", zIndex: 1 }}
                >
                  - Confirm to load large image (28Mb) -
                  <br />
                  <button
                    type="button"
                    className="btn btn-success"
                    onClick={() => {
                      setBigImageActive(true);
                    }}
                    style={{ marginTop: "0.5em" }}
                  >
                    <FontAwesomeIcon icon={faHandPointRight} /> Continue
                  </button>
                </div>
              </div>
              <img
                src="https://staticbrainz.org/LB/year-in-music/2022/rainbow1-100-7-small.jpeg"
                srcSet="https://staticbrainz.org/LB/year-in-music/2022/rainbow1-100-7-small.jpeg 500w,
              https://staticbrainz.org/LB/year-in-music/2022/rainbow1-100-7-medium.jpeg 1000w"
                alt="2022 albums"
              />
            </>
          ) : (
            <>
              <img
                ref={targetRef}
                src="https://staticbrainz.org/LB/year-in-music/2022/rainbow1-100-7.jpg"
                useMap="#cover-image-map"
                alt="Albums"
                onLoad={setInitialZoom}
              />
              <map name="cover-image-map">
                {jsonMap.map((coverDef: CoverDef) => {
                  const { x1, x2, y1, y2, name, release_mbid } = coverDef;
                  const coordinates = [x1, y1, x2, y2].join();
                  return (
                    <area
                      key={`${name}-${coordinates}`}
                      shape="rect"
                      coords={coordinates}
                      alt={name}
                      href={
                        preventClick ? undefined : `/release/${release_mbid}/`
                      }
                    />
                  );
                })}
              </map>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
