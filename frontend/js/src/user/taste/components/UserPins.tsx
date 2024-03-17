/* eslint-disable jsx-a11y/anchor-is-valid */

import { createRoot } from "react-dom/client";
import * as React from "react";

import * as _ from "lodash";

import { toast } from "react-toastify";
import { Link } from "react-router-dom";
import GlobalAppContext from "../../../utils/GlobalAppContext";
import Loader from "../../../components/Loader";
import PinnedRecordingCard from "../../components/PinnedRecordingCard";
import {
  getListenablePin,
  getRecordingMBID,
  getRecordingMSID,
} from "../../../utils/utils";
import { ToastMsg } from "../../../notifications/Notifications";

export type UserPinsProps = {
  user: ListenBrainzUser;
  pins: PinnedRecording[];
  totalCount: number;
  profileUrl?: string;
};

export type UserPinsState = {
  pins: PinnedRecording[];
  page: number;
  maxPage: number;
  loading: boolean;
  noMorePins: boolean;
};

export default class UserPins extends React.Component<
  UserPinsProps,
  UserPinsState
> {
  static contextType = GlobalAppContext;
  declare context: React.ContextType<typeof GlobalAppContext>;

  private DEFAULT_PINS_PER_PAGE = 25;

  constructor(props: UserPinsProps) {
    super(props);
    const { totalCount } = this.props;
    const maxPage = Math.ceil(totalCount / this.DEFAULT_PINS_PER_PAGE);
    this.state = {
      maxPage,
      page: 1,
      pins: props.pins || [],
      loading: false,
      noMorePins: maxPage <= 1,
    };
  }

  handleLoadMore = async (event?: React.MouseEvent) => {
    const { page, maxPage } = this.state;
    if (page >= maxPage) {
      return;
    }

    await this.getPinsFromAPI(page + 1);
  };

  getPinsFromAPI = async (page: number, replacePinsArray: boolean = false) => {
    const { user } = this.props;
    const { APIService } = this.context;
    const { pins } = this.state;
    this.setState({ loading: true });

    try {
      const limit = (page - 1) * this.DEFAULT_PINS_PER_PAGE;
      const count = this.DEFAULT_PINS_PER_PAGE;
      const newPins = await APIService.getPinsForUser(user.name, limit, count);

      if (!newPins.pinned_recordings.length) {
        // No pins were fetched
        this.setState({
          loading: false,
          pins: replacePinsArray ? [] : pins,
          noMorePins: true,
        });
        return;
      }

      const totalCount = parseInt(newPins.total_count, 10);
      const newMaxPage = Math.ceil(totalCount / this.DEFAULT_PINS_PER_PAGE);
      this.setState({
        loading: false,
        page,
        maxPage: newMaxPage,
        pins: replacePinsArray
          ? newPins.pinned_recordings
          : pins.concat(newPins.pinned_recordings),
        noMorePins: page >= newMaxPage,
      });
    } catch (error) {
      toast.warn(
        <ToastMsg
          title="Could not load pin history"
          message={
            <>
              Something went wrong when we tried to load your pinned recordings,
              please try again or contact us if the problem persists.
              <br />
              <strong>
                {error.name}: {error.message}
              </strong>
            </>
          }
        />,
        { toastId: "load-pins-error" }
      );
      this.setState({ loading: false });
    }
  };

  removePinFromPinsList = (pin: PinnedRecording) => {
    const { pins } = this.state;
    const index = pins.indexOf(pin);

    pins.splice(index, 1);
    this.setState({ pins });
  };

  render() {
    const { user, profileUrl } = this.props;
    const { pins, loading, noMorePins } = this.state;
    const { currentUser } = this.context;

    const pinsAsListens = pins.map((pin) => {
      return getListenablePin(pin);
    });

    return (
      <div>
        <div className="listen-header">
          <h3 className="header-with-line">
            {user.name === currentUser.name
              ? "Your"
              : `${_.startCase(user.name)}'s`}{" "}
            Pins
          </h3>
        </div>

        {pins.length === 0 && (
          <>
            <div className="lead text-center">No pins yet</div>

            {user.name === currentUser.name && (
              <>
                Pin one of your
                <Link to={`${profileUrl ?? "/my/listens/"}`}>
                  {" "}
                  recent Listens!
                </Link>
              </>
            )}
          </>
        )}

        {pins.length > 0 && (
          <div>
            <div
              style={{
                height: 0,
                position: "sticky",
                top: "50%",
                zIndex: 1,
              }}
            >
              <Loader isLoading={loading} />
            </div>
            <div
              id="pinned-recordings"
              style={{ opacity: loading ? "0.4" : "1" }}
            >
              {pins?.map((pin, index) => {
                return (
                  <PinnedRecordingCard
                    key={pin.created}
                    pinnedRecording={pin}
                    isCurrentUser={currentUser?.name === user?.name}
                    removePinFromPinsList={this.removePinFromPinsList}
                  />
                );
              })}
              <button
                className={`mt-15 btn btn-block ${
                  noMorePins ? "btn-default" : "btn-info"
                }`}
                disabled={noMorePins}
                type="button"
                onClick={this.handleLoadMore}
                title="Load more…"
              >
                {noMorePins ? "No more pins to show" : "Load more…"}
              </button>
            </div>
          </div>
        )}
      </div>
    );
  }
}
