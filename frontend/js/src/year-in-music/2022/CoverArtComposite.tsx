import React, { useCallback, useEffect, useRef, useState } from "react";
import panzoom, { PanZoom } from "panzoom";
import * as jsonMap from "./rainbow1-100-7.jpg.json";

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
    if (!targetRef.current) return;

    const container = targetRef.current.parentElement as HTMLDivElement;
    const containerWidth = container.clientWidth;
    const imageWidth = 10000;
    const lowestZoom = containerWidth / imageWidth;
    const createdPanZoomInstance = panzoom(targetRef.current, {
      maxZoom: 1,
      minZoom: lowestZoom,
      bounds: true,
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
  }, []);

  return (
    <div
      id="year-in-music"
      className="yim-2022"
      style={{
        textAlign: "center",
        backgroundColor: "#ff0e25",
        color: "#ffcc49",
      }}
    >
      <div className="red-section">
        <div className="header">
          Album covers of 2022
          <div className="subheader">
            Zoom, pan and click to go to a playable album page
          </div>
        </div>
        <button
          type="button"
          className="btn btn-default"
          onClick={setInitialZoom}
        >
          Reset
        </button>
        <div style={{ width: "100%", height: "70vh", overflow: "hidden" }}>
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
                    preventClick
                      ? undefined
                      : `//musicbrainz.org/release/${release_mbid}`
                  }
                  target="_blank"
                  rel="noopener noreferrer"
                />
              );
            })}
          </map>
        </div>
      </div>
    </div>
  );
}
