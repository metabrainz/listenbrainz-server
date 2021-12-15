import html2canvas from "html2canvas";
import React from "react";
import {
  faCamera,
  faPlay,
  faHeadphones,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { IconProp } from "@fortawesome/fontawesome-svg-core";
import ListenCard from "../listens/ListenCard";
import { getEntityLink } from "../stats/utils";

export type ComponentToImageProps = {
  data: any[];
  entityType: Entity;
  user: ListenBrainzUser;
};

const ComponentToImage = ({
  data,
  entityType,
  user,
}: ComponentToImageProps) => {
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
  };

  const exportAsPicture = () => {
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
      windowWidth: document.documentElement.offsetWidth,
      windowHeight: document.documentElement.offsetHeight,
    })
      .then((canvas) => {
        return canvas.toDataURL("image/png", 1.0);
      })
      .then((image) => {
        saveAs(image, `${user.name}-top-${entityType}s-2021.png`);
      });
  };

  return (
    <>
      <button
        className="btn btn-primary"
        onClick={exportAsPicture}
        type="button"
      >
        <FontAwesomeIcon
          className="col-6"
          size="1x"
          style={{ marginRight: "4px" }}
          icon={faCamera as IconProp}
        />
        Share as Image
      </button>
      <div id={`savable-${entityType}-component`} className="savable-card card">
        <img
          className="card-img-top"
          src="/static/img/year-in-music-2021.svg"
          alt="Your year in music 2021"
        />
        {/* <h2 className="card-title">Year In Music 2021</h2> */}
        <h5 className="card-title">
          {user.name}&apos;s top {entityType}s of 2021
        </h5>
        <div className="list-container">
          {(() => {
            if (entityType === "artist") {
              return data.map((artist) => {
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
                    thumbnail={thumbnail}
                    listenDetails={details}
                    showTimestamp={false}
                    showUsername={false}
                    newAlert={() => {}}
                  />
                );
              });
            }
            // if (entityType === "release") {
            //   return data.map((release) => (
            //     <li className="list-group-item">{release.release_name}</li>
            //   ));
            // }
            return data.map((recording) => (
              // <li className="list-group-item">{recording.track_name}</li>
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
                newAlert={() => {}}
              />
            ));
          })()}
        </div>
        <div className="card-footer">
          <p className="card-text">
            <small className="text-muted">
              Find your stats at{" "}
              <a href="https://listenbrainz.org">listenbrainz.org</a>
            </small>
          </p>
          <img
            className="card-img-bottom"
            src="/static/img/listenbrainz-logo.svg"
            style={{ width: "16rem", padding: "1rem" }}
            alt="ListenBrainz"
          />
        </div>
      </div>
    </>
  );
};

export default ComponentToImage;
