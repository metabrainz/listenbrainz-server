import * as React from "react";
import { faSpinner } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { IconProp } from "@fortawesome/fontawesome-svg-core";

type LoaderProps = {
  isLoading: boolean;
};

const Loader: React.SFC<LoaderProps> = (props) => {
  // eslint-disable-next-line react/prop-types
  const { isLoading, children } = props;
  return isLoading ? (
    <FontAwesomeIcon icon={faSpinner as IconProp} size="4x" spin />
  ) : (
    <>{children}</>
  );
};

export default Loader;
