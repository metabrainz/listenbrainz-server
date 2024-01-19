import html2canvas from "html2canvas";
import React, { useState } from "react";
import { faCamera, faHeadphones } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { IconProp } from "@fortawesome/fontawesome-svg-core";
import ListenCard from "../../../../common/listens/ListenCard";
import { getEntityLink } from "../../../stats/utils";
import Loader from "../../../../components/Loader";

export type ComponentToImageProps = {
  data: any[];
  entityType: Entity;
  user: ListenBrainzUser;
};

function ComponentToImage({ data, entityType, user }: ComponentToImageProps) {
  const [isLoading, setIsLoading] = useState(false);
  const saveAs = (blob: string, fileName: string) => {
    const elem = window.document.createElement("a");
    elem.href = blob;
    elem.download = fileName;
    (document.body || document.documentElement).appendChild(elem);
    if (typeof elem.click === "function") {
      elem.click();
    } else {
      elem.target = "_blank";
      elem.dispatchEvent(
        new MouseEvent("click", {
          view: window,
          bubbles: true,
          cancelable: true,
        })
      );
    }
    URL.revokeObjectURL(elem.href);
    elem.remove();
    setIsLoading(false);
  };

  const exportAsPicture = () => {
    setIsLoading(true);
    const targetId = `savable-${entityType}-component`;
    const element = document.getElementById(targetId);
    html2canvas(element as HTMLElement, {
      onclone(clonedDoc) {
        // eslint-disable-next-line no-param-reassign
        clonedDoc!.getElementById(targetId)!.style.display = "block";
      },
      useCORS: true,
      allowTaint: true,
      imageTimeout: 30000,
      scrollX: -window.scrollX,
      scrollY: -window.scrollY,
      windowWidth: element!.offsetWidth,
      windowHeight: element!.offsetHeight,
    })
      .then((canvas) => {
        return canvas.toDataURL("image/png", 1.0);
      })
      .then((image) => {
        saveAs(image, `${user.name}-top-${entityType}s-2022.png`);
      });
  };

  return (
    <>
      <button
        className="btn btn-primary"
        onClick={exportAsPicture}
        type="button"
      >
        <Loader isLoading={isLoading} loaderText="Generating image…">
          <FontAwesomeIcon
            className="col-6"
            size="1x"
            style={{ marginRight: "4px" }}
            icon={faCamera as IconProp}
          />
          Save as image
        </Loader>
      </button>
      <div id={`savable-${entityType}-component`} className="savable-card card">
        <img
          className="card-img-top"
          src="/static/img/year-in-music-2021.png"
          alt="Your year in music 2022"
        />
        <h3 className="card-title">
          {user.name}&apos;s top {entityType}s of 2022
        </h3>
        {entityType === "release" && (
          <div className="grid">
            {data.slice(0, 9).map((release) => (
              <img src={release.cover_art_src} alt={release.release_name} />
            ))}
          </div>
        )}
        {entityType === "artist" && (
          <div className="list-container">
            {data.map((artist) => {
              const details = getEntityLink(
                "artist",
                artist.artist_name,
                artist.artist_mbids[0]
              );
              const thumbnail = (
                <span className="badge badge-info">
                  <FontAwesomeIcon
                    style={{ marginRight: "4px" }}
                    icon={faHeadphones as IconProp}
                  />
                  {artist.listen_count}
                </span>
              );
              return (
                <ListenCard
                  compact
                  key={`top-artists-${artist.artist_name}-${artist.artist_mbids}`}
                  listen={{
                    listened_at: 0,
                    track_metadata: {
                      track_name: "",
                      artist_name: artist.artist_name,
                      additional_info: {
                        artist_mbids: artist.artist_mbids,
                      },
                    },
                  }}
                  customThumbnail={thumbnail}
                  listenDetails={details}
                  showTimestamp={false}
                  showUsername={false}
                />
              );
            })}
          </div>
        )}
        {entityType === "recording" && (
          <div className="list-container">
            {data.map((recording) => (
              <ListenCard
                compact
                key={`top-recordings-${recording.recording_mbid}`}
                listen={{
                  listened_at: 0,
                  track_metadata: {
                    artist_name: recording.artist_name,
                    track_name: recording.track_name,
                    release_name: recording.release_name,
                    additional_info: {
                      recording_mbid: recording.recording_mbid,
                      release_mbid: recording.release_mbid,
                      artist_mbids: recording.artist_mbids,
                    },
                  },
                }}
                showTimestamp={false}
                showUsername={false}
              />
            ))}
          </div>
        )}
        <div className="card-footer">
          <p className="card-text">
            <small className="text-muted">
              Find your stats at{" "}
              <a href="https://listenbrainz.org">listenbrainz.org</a>
            </small>
          </p>
          <img
            className="card-img-bottom"
            src="/static/img/listenbrainz-logo.png"
            alt="ListenBrainz"
          />
        </div>
      </div>
    </>
  );
}

export default ComponentToImage;
