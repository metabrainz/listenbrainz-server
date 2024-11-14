import * as React from "react";
import { Link } from "react-router-dom";
import useUserFlairs from "../utils/FlairLoader";
import { Flair } from "../utils/constants";

interface BaseUsernameProps extends React.HTMLAttributes<HTMLElement> {
  username: string;
  hideFlair?: boolean;
  // Allow overriding the flair (for example for flair preview)
  selectedFlair?: Flair;
}

type WithLinkProps = BaseUsernameProps & {
  hideLink?: false;
  elementType?: undefined;
};

type WithElementProps = BaseUsernameProps & {
  hideLink: true;
  elementType: keyof HTMLElementTagNameMap;
};

function Username(props: WithLinkProps | WithElementProps) {
  const {
    username,
    elementType = "div",
    hideFlair = false,
    hideLink = false,
    selectedFlair,
    ...otherProps
  } = props;

  const savedFlairType = useUserFlairs(username);
  const flairType = selectedFlair ?? savedFlairType;
  const cssClasses = `${otherProps?.className || ""} ${
    !hideFlair ? `flair ${flairType || ""}` : ""
  }`;

  let htmlContent: string | JSX.Element[] = username;
  switch (flairType) {
    /*
      Split each letter into a span element to allow animating each letter separately
      Only required for some animation (see the flairs.less file)
    */
    case "flip-3d":
    case "flip-horizontal":
    case "flip-vertical":
    case "lb-colors-sweep":
    case "light-sweep":
    case "wave":
    case "tornado":
      htmlContent = username.split("").map((letter, i) => (
        // eslint-disable-next-line react/no-array-index-key
        <span key={username + letter + i}>{letter}</span>
      ));
      break;
    default:
      break;
  }

  if (!hideLink) {
    return (
      <Link
        to={`/user/${username}/`}
        {...otherProps}
        className={cssClasses}
        title={username}
        data-text={username}
      >
        {htmlContent}
      </Link>
    );
  }

  return React.createElement(
    elementType,
    {
      ...otherProps,
      className: cssClasses,
      title: username,
      "data-text": username,
    },
    htmlContent
  );
}

export default Username;
