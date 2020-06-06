/* eslint-disable react/prefer-stateless-function */
import * as React from "react";
import { faSpinner } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { IconProp } from "@fortawesome/fontawesome-svg-core";

type withLoaderProps = {
  isLoading: boolean;
};

const withLoader = <P extends object>(Component: React.ComponentType<P>) => {
  return class WithLoader extends React.Component<P & withLoaderProps> {
    render() {
      const { isLoading, ...props } = this.props;
      // TODO: Replace with Bootstrap 4 spinner when we upgrade
      return isLoading ? (
        <FontAwesomeIcon icon={faSpinner as IconProp} size="4x" spin />
      ) : (
        <Component {...(props as P)} />
      );
    }
  };
};

export default withLoader;
