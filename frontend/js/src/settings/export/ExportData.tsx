import * as React from "react";

import { Helmet } from "react-helmet";
import GlobalAppContext from "../../utils/GlobalAppContext";
import ExportButtons from "./ExportButtons";

export default function Export() {
  const { currentUser } = React.useContext(GlobalAppContext);

  return (
    <>
      <Helmet>
        <title>Export for {currentUser?.name}</title>
      </Helmet>
      <h3>Export from ListenBrainz</h3>
      <ExportButtons />
    </>
  );
}
