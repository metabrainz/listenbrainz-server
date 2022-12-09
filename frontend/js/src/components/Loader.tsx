import * as React from "react";
import Spinner from "react-loader-spinner";

type LoaderProps = {
  isLoading: boolean;
  style?: React.CSSProperties;
  className?: string;
  loaderText?: string;
  [key: string]: any;
};

export default function Loader(
  props: React.PropsWithChildren<LoaderProps>
): JSX.Element {
  const {
    isLoading,
    children,
    className,
    loaderText,
    style: propStyle,
    ...rest
  } = props;

  const style: React.CSSProperties = {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    minHeight: "inherit",
    ...propStyle,
  };

  return isLoading ? (
    <div className={`text-center ${className || ""}`} style={style} {...rest}>
      <Spinner type="Oval" color="#cccccc" height={30} width={30} />
      {loaderText && (
        <small>
          <p className="text-muted mt-5">{loaderText}</p>
        </small>
      )}
    </div>
  ) : (
    // eslint-disable-next-line react/jsx-no-useless-fragment
    <>{children}</>
  );
}
