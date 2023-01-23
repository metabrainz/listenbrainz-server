import * as React from "react";
import { faTimesCircle } from "@fortawesome/free-solid-svg-icons";
import { throttle as _throttle } from "lodash";
import DateTimePicker from "react-datetime-picker/dist/entry.nostyle";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { IconProp } from "@fortawesome/fontawesome-svg-core";
import { faCalendar } from "@fortawesome/free-regular-svg-icons";
import ListenControl from "../listens/ListenControl";
import {
  getAlbumArtFromReleaseMBID,
  convertDateToUnixTimestamp,
} from "../utils/utils";
import GlobalAppContext from "../utils/GlobalAppContext";

export type SubmitListenInfoState = {
  thumbnailSrc: string;
  customTimestamp: Boolean;
  selectedDate: Date;
  searchField: string;
  trackResults: Array<ACRMSearchResult>;
  selectedTrack: ACRMSearchResult;
  trackIsSelected: Boolean;
};

export type SubmitListenInfoProps = {
  trackMetadata: (event: ACRMSearchResult) => void;
  dateToUnixTimestamp: (event: number) => void;
  isTrackReset: Boolean;
  isListenSubmit: Boolean;
};

export default class SubmitListenInfo extends React.Component<
  SubmitListenInfoProps,
  SubmitListenInfoState
> {
  static contextType = GlobalAppContext;
  declare context: React.ContextType<typeof GlobalAppContext>;

  constructor(props: SubmitListenInfoProps) {
    super(props);

    this.state = {
      thumbnailSrc: "/static/img/cover-art-placeholder.jpg",
      customTimestamp: false,
      selectedDate: new Date(),
      searchField: "",
      trackResults: [],
      selectedTrack: {
        artist_credit_id: 0,
        artist_credit_name: "",
        recording_mbid: "",
        recording_name: "",
        release_mbid: "",
        release_name: "",
      },
      trackIsSelected: false,
    };
  }

  componentDidMount() {
    this.convertToUnix();
  }

  componentDidUpdate(pp: any, ps: any, ss: any) {
    const { trackIsSelected, selectedDate } = this.state;
    const { isTrackReset, isListenSubmit } = this.props;
    if (ps.TrackIsSelected !== trackIsSelected) {
      this.getCoverArt();
    }
    if (ps.selectedDate !== selectedDate) {
      this.convertToUnix();
    }
    if (pp.isTrackReset !== isTrackReset) {
      this.removeTrack();
    }
    if (pp.isListenSubmit !== isListenSubmit) {
      this.removeTrack();
    }
  }

  async getCoverArt() {
    const { selectedTrack } = this.state;
    const albumArtSrc = await getAlbumArtFromReleaseMBID(
      selectedTrack.release_mbid
    );
    if (albumArtSrc) {
      this.setState({ thumbnailSrc: albumArtSrc });
    }
  }

  timestampNow = () => {
    this.setState({
      customTimestamp: false,
      selectedDate: new Date(),
    });
  };

  timestampCustom = () => {
    this.setState({
      customTimestamp: true,
      selectedDate: new Date(),
    });
  };

  convertToUnix = () => {
    const { selectedDate } = this.state;
    const { dateToUnixTimestamp } = this.props;
    console.log(convertDateToUnixTimestamp(selectedDate));
    dateToUnixTimestamp(convertDateToUnixTimestamp(selectedDate));
  };

  onChangeDateTimePicker = async (newDateTimePickerValue: Date) => {
    this.setState({
      selectedDate: newDateTimePickerValue,
    });
  };

  SearchTrack = async () => {
    const { searchField } = this.state;
    try {
      const response = await fetch(
        "https://labs.api.listenbrainz.org/recording-search/json",
        {
          method: "POST",
          body: JSON.stringify([{ query: searchField }]),
          headers: {
            "Content-type": "application/json; charset=UTF-8",
          },
        }
      );

      const parsedResponse = await response.json();
      this.setState({
        trackResults: parsedResponse,
      });
    } catch (error) {
      console.debug(error);
    }
  };

  TrackName = (event: React.ChangeEvent<HTMLInputElement>) => {
    this.setState(
      {
        searchField: event.target.value,
      },
      () => {
        this.SearchTrack();
      }
    );
  };

  // eslint-disable-next-line react/sort-comp
  throttledHandleInputChange = _throttle(this.TrackName, 300);

  addTrackMetadata = (track: ACRMSearchResult) => {
    this.setState({
      selectedTrack: track,
      trackIsSelected: true,
    });
    const { trackMetadata } = this.props;
    trackMetadata(track);
  };

  removeTrack = () => {
    this.setState({
      thumbnailSrc: "/static/img/cover-art-placeholder.jpg",
      customTimestamp: false,
      selectedDate: new Date(),
      searchField: "",
      trackResults: [],
      selectedTrack: {
        artist_credit_id: 0,
        artist_credit_name: "",
        recording_mbid: "",
        recording_name: "",
        release_mbid: "",
        release_name: "",
      },
      trackIsSelected: false,
    });
  };

  render() {
    const {
      thumbnailSrc,
      customTimestamp,
      selectedDate,
      selectedTrack,
      trackIsSelected,
      searchField,
      trackResults,
    } = this.state;

    return trackIsSelected === false ? (
      <div>
        <input
          type="text"
          className="form-control add-track-field"
          onChange={this.throttledHandleInputChange}
          placeholder="Add Artist name followed by Track name"
          value={searchField}
        />
        <div className="tracksearchdropdown">
          {trackResults?.map((track) => {
            return (
              <button
                type="button"
                onClick={() => this.addTrackMetadata(track)}
              >
                {`${track.recording_name} - ${track.artist_credit_name}`}
              </button>
            );
          })}
        </div>
      </div>
    ) : (
      <div>
        <div className="addtrackpill">
          <div>
            <span>{`${selectedTrack.recording_name} - ${selectedTrack.artist_credit_name}`}</span>
            <ListenControl
              text=""
              icon={faTimesCircle}
              action={this.removeTrack}
            />
          </div>
        </div>
        <div className="track-info">
          <div className="cover-art-img">
            <img
              src={thumbnailSrc}
              alt={selectedTrack?.release_name ?? "cover art"}
            />
          </div>
          <div style={{ display: "block", width: "100%" }}>
            <div className="track-details" style={{ marginTop: "23px" }}>
              <div className="listen-entity">
                <span>Track</span>
              </div>
              <div className="entity-details">
                <span>{`${selectedTrack?.recording_name}`}</span>
              </div>
            </div>
            <div className="track-details">
              <div className="listen-entity">
                <span>Artist</span>
              </div>
              <div className="entity-details">
                <span>{`${selectedTrack?.artist_credit_name}`}</span>
              </div>
            </div>
            <div className="track-details">
              <div className="listen-entity">
                <span>Album</span>
              </div>
              <div className="entity-details">
                <span>{`${selectedTrack?.release_name}`}</span>
              </div>
            </div>
            <div className="timestamp">
              <span>Timestamp</span>
              <button
                type="button"
                className={`btn btn-primary add-listen ${
                  customTimestamp === false
                    ? "timestamp-active"
                    : "timestamp-unactive"
                }`}
                onClick={this.timestampNow}
              >
                Now
              </button>
              <button
                type="button"
                className={`btn btn-primary add-listen ${
                  customTimestamp === true
                    ? "timestamp-active"
                    : "timestamp-unactive"
                }`}
                onClick={this.timestampCustom}
              >
                Custom
              </button>
            </div>
            <div className="timestamp-date-picker">
              <DateTimePicker
                value={selectedDate}
                onChange={this.onChangeDateTimePicker}
                calendarIcon={<FontAwesomeIcon icon={faCalendar as IconProp} />}
                maxDate={new Date(Date.now())}
                clearIcon={null}
                format="dd/MM/yyyy h:mm:ss a"
                disabled={!customTimestamp}
              />
            </div>
          </div>
        </div>
      </div>
    );
  }
}
