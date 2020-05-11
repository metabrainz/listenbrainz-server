import * as React from "react";

export default class ErrorBoundary extends React.Component<any, any> {
  constructor(props: any) {
    super(props);

    this.state = { hasError: false, error: null };
  }

  componentDidCatch(error: Error) {
    // Update state so the next render will show the fallback UI.
    this.setState({ hasError: true, error });
  }

  render() {
    const { children } = this.props;
    const { hasError, error } = this.state;

    if (hasError) {
      document.title = "Something went wrong - Listenbrainz";
      return (
        <div>
          <h2 className="page-title">{error.name}</h2>
          <p>{error.message}</p>
          <p>
            <a href={`//${window.location.href.split("/")[2]}`}>
              Back to home page
            </a>
          </p>
        </div>
      );
    }

    return children;
  }
}
