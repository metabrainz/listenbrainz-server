import * as React from "react";
import MediaQuery from "react-responsive";
import PaymentButton from "./PaymentButton";

type PatronTimeRange = "all_time" | "month";

type PatronPaymentButtonsProps = {};

type PatronPaymentButtonsState = {
  timeRange: PatronTimeRange;
};

class PatronPaymentButtons extends React.Component<
  PatronPaymentButtonsProps,
  PatronPaymentButtonsState
> {
  constructor(props: PatronPaymentButtonsProps) {
    super(props);
    this.state = {
      timeRange: "month",
    };
  }

  changeRange = (range: "month" | "all_time", event: any) => {
    this.setState({ timeRange: range });
  };

  renderAllTimePaymentButtons = () => {
    return (
      <div
        style={{
          justifyContent: "center",
          alignItems: "center",
          display: "flex",
        }}
      >
        <PaymentButton amount={100} timeRange="all_time" />
      </div>
    );
  };

  renderMonthPaymentButtons = () => {
    return (
      <>
        <MediaQuery minWidth={768}>
          <div
            className="row"
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <PaymentButton amount={5} timeRange="month" />
            <PaymentButton amount={10} timeRange="month" />
            <PaymentButton amount={20} timeRange="month" />
            <PaymentButton amount={50} timeRange="month" />
          </div>
        </MediaQuery>
        <MediaQuery maxWidth={767}>
          <div
            className="row"
            style={{
              display: "flex",
              justifyContent: "center",
            }}
          >
            <PaymentButton amount={5} timeRange="month" />
          </div>
          <div
            className="row"
            style={{ display: "flex", justifyContent: "center" }}
          >
            <PaymentButton amount={10} timeRange="month" />
          </div>
          <div
            className="row"
            style={{ display: "flex", justifyContent: "center" }}
          >
            <PaymentButton amount={20} timeRange="month" />
          </div>
          <div
            className="row"
            style={{ display: "flex", justifyContent: "center" }}
          >
            <PaymentButton amount={50} timeRange="month" />
          </div>
        </MediaQuery>
      </>
    );
  };

  renderTimeRangeWithDropdown = () => {
    const { timeRange } = this.state;
    return (
      <>
        <span className="dropdown" style={{ fontSize: 22 }}>
          <button
            className="dropdown-toggle btn-transparent"
            data-toggle="dropdown"
            type="button"
          >
            {timeRange === "month" && <b>a month</b>}
            {timeRange === "all_time" && <b>all time</b>}
            <span className="caret" />
          </button>
          <ul className="dropdown-menu" role="menu">
            <li>
              {/* eslint-disable-next-line jsx-a11y/anchor-is-valid */}
              <a
                role="button"
                onClick={(event) => this.changeRange("month", event)}
                onKeyPress={(event) => this.changeRange("month", event)}
                tabIndex={0}
              >
                Month
              </a>
            </li>
            <li>
              {/* eslint-disable-next-line jsx-a11y/anchor-is-valid */}
              <a
                role="button"
                onClick={(event) => this.changeRange("all_time", event)}
                onKeyPress={(event) => this.changeRange("all_time", event)}
                tabIndex={0}
              >
                All time
              </a>
            </li>
          </ul>
        </span>
      </>
    );
  };

  render() {
    const { timeRange } = this.state;
    return (
      <div
        role="main"
        style={{
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <h3 style={{ textAlign: "center" }}>
          Become a patron for{this.renderTimeRangeWithDropdown()}
        </h3>
        {timeRange === "all_time" && this.renderAllTimePaymentButtons()}
        {timeRange === "month" && this.renderMonthPaymentButtons()}
      </div>
    );
  }
}

export default PatronPaymentButtons;
