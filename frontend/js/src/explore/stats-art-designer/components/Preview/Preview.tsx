import * as React from "react";

type PreviewProps = {
  url: string;
};

function Preview(props: PreviewProps) {
  const { url } = props;
  return <object className="preview" title="preview" data={url} />;
}

export default Preview;
