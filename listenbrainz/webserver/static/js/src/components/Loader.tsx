import * as React from "react";
import { faSpinner } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { IconProp } from "@fortawesome/fontawesome-svg-core";

type LoaderProps = {
  isLoading: boolean;
  style?: React.CSSProperties;
  className?: string;
  [key: string]: any;
};

export default function Loader(props: React.PropsWithChildren<LoaderProps>) {
  const { isLoading, children, className, ...rest } = props;
  return isLoading ? (
    <div className={`text-center ${className || ""}`} {...rest}>
      <FontAwesomeIcon icon={faSpinner as IconProp} size="4x" spin />
    </div>
  ) : (
    <>{children}</>
  );
}
