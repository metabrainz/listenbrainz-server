import html2canvas from "html2canvas";
import React from "react";
import { faCamera, faPlay } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { IconProp } from "@fortawesome/fontawesome-svg-core";

export type ComponentToImageProps = {
  data: any[];
  entity: string;
};

const ComponentToImage = ({ data, entity }: ComponentToImageProps) => {
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
    const element = document.getElementById("card");
    html2canvas(element as HTMLElement, {
      onclone(clonedDoc) {
        // eslint-disable-next-line no-param-reassign
        clonedDoc!.getElementById("card")!.style.display = "block";
      },
    })
      .then((canvas) => {
        return canvas.toDataURL("image/png", 1.0);
      })
      .then((image) => {
        saveAs(image, `${{ entity }}.png`);
      });
  };

  return (
    <>
      <button
        className="col-6 btn-primary center"
        style={{ marginLeft: "2rem", marginBottom: "1rem" }}
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
      <div
        id="card"
        className="card text-center justify-content-center align-content-center align-items-center"
        style={{ width: "24rem", display: "none" }}
      >
        <img
          className="card-img-top"
          src="/static/img/listenbrainz-logo.svg"
          style={{ width: "16rem", padding: "1rem" }}
          alt="ListenBrainz"
        />
        <h2 className="card-title">Year In Music 2021</h2>
        <h5 className="card-title">akshaaatt&apos;s Top {entity}</h5>
        <img
          className="card-img-top"
          src="/static/img/logo_big.svg"
          style={{
            width: "128px",
            height: "128px",
            padding: "4px",
            margin: "4px",
          }}
          alt=""
        />
        <ul className="list-group list-group-flush">
          {(() => {
            if (entity === "Artists") {
              return data.map((release) => (
                <li className="list-group-item">{release.artist_name}</li>
              ));
            }
            if (entity === "Releases") {
              return data.map((release) => (
                <li className="list-group-item">{release.release_name}</li>
              ));
            }
            return data.map((release) => (
              <li className="list-group-item">{release.track_name}</li>
            ));
          })()}
        </ul>
        <div className="card-body">
          <p className="card-text">
            <small className="text-muted">
              Find your Stats at{" "}
              <a href="https://listenbrainz.org">listenbrainz.org</a>
            </small>
          </p>
        </div>
      </div>
    </>
  );
};

export default ComponentToImage;
