import * as React from "react";
import "./Preview.css";

type PreviewProps = {
  url: string;
};

function Preview(props: PreviewProps) {
  const { url } = props;
  return (
    <object
      className="preview"
      title="preview"
      data={url}
      width={700}
      height={700}
    />
  );
}

export default Preview;
