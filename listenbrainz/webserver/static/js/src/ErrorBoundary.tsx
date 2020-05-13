import * as React from "react";

export type ErrorBoundaryState = {
  hasError: boolean;
  error: Error | null;
};

export default class ErrorBoundary extends React.Component<
  {},
  ErrorBoundaryState
> {
  constructor(props: {}) {
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
      document.title = "Something went wrong - ListenBrainz";
      return (
        <div>
          <h2 className="page-title">{error!.name}</h2>
          <p>{error!.message}</p>
          <p>
            <button
              className="btn-link"
              type="button"
              onClick={() => {
                window.location.reload();
              }}
            >
              Reload the page
            </button>
          </p>
        </div>
      );
    }

    return children;
  }
}
