import * as React from "react";
import { Helmet } from "react-helmet";

type CACProps = {
  year: number;
};

export function CACYearStyleTags({ year }: CACProps) {
  if (year === 2022) {
    return (
      <Helmet>
        <style type="text/css">
          {`#react-container {
            background-color: #ff0e25;
          }
          #container-react {
            overflow: hidden;
          }`}
        </style>
      </Helmet>
    );
  }
  return (
    <Helmet>
      <style type="text/css">
        {`#react-container {
            background-color: #F0EEE2;
          }
          #container-react {
            overflow: hidden;
          }`}
      </style>
    </Helmet>
  );
}

export default function SEO(props: CACProps) {
  const { year } = props;

  return (
    <Helmet>
      <title>{`Album covers of ${year}`}</title>
      <style type="text/css">
        {`body {
            padding-bottom: 0;
        }
        body>:not(nav){
            padding-bottom: 0;
        }
        #react-container {
            margin: 0 -15px 0;
            padding:0;
            height: 100vh;
        }
        section.footer{
            display: none;
        }`}
      </style>
    </Helmet>
  );
}
