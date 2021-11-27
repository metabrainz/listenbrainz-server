import html2canvas from "html2canvas";
import React from "react";

const ComponentToImage = () => {
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
    const html = document.getElementsByTagName("HTML")[0] as HTMLElement;
    const body = document.getElementsByTagName("BODY")[0] as HTMLElement;
    let htmlWidth = html.clientWidth;
    let bodyWidth = body.clientWidth;

    const data = document.getElementById("card");
    const newWidth = data!.scrollWidth - data!.clientWidth;

    if (newWidth > data!.clientWidth) {
      htmlWidth += newWidth;
      bodyWidth += newWidth;
    }

    html.style.width = `${htmlWidth}px`;
    body.style.width = `${bodyWidth}px`;

    html2canvas(data as HTMLElement)
      .then((canvas) => {
        return canvas.toDataURL("image/png", 1.0);
      })
      .then((image) => {
        saveAs(image, "year-in-music.png");
      });
  };

  return (
    <div className="row text-center justify-content-center align-content-center align-items-center">
      <div id="card" className="col-sm-8 card" style={{ width: "24rem" }}>
        <img
          className="card-img-top"
          src="/static/img/listenbrainz-logo.svg"
          style={{ width: "16rem", padding: "1rem" }}
          alt="ListenBrainz"
        />
        <h2 className="card-title">Year In Music 2021</h2>
        <h5 className="card-title">akshaaatt&apos;s Top Artists</h5>
        <img
          className="card-img-top"
          src="/static/img/logo_big.svg"
          style={{
            width: "128px",
            height: "128px",
            padding: "4px",
            margin: "4px",
          }}
          alt="Tickets to my Downfall"
        />
        <ul className="list-group list-group-flush">
          <li className="list-group-item">Linkin Park</li>
          <li className="list-group-item">Machine Gun Kelly</li>
          <li className="list-group-item">Troye Sivan</li>
          <li className="list-group-item">Bring Me The Horizon</li>
          <li className="list-group-item">Maroon 5</li>
          <li className="list-group-item">Mike Shinoda</li>
          <li className="list-group-item">Lauv</li>
          <li className="list-group-item">Arctic Monkeys</li>
          <li className="list-group-item">Halsey</li>
          <li className="list-group-item">Ed Sheeran</li>
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
      <button
        className="col-sm-4"
        style={{ margin: "5rem" }}
        onClick={exportAsPicture}
      >
        Save as Image
      </button>
    </div>
  );
};

export default ComponentToImage;
