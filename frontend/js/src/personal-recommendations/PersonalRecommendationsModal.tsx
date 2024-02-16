import * as React from "react";
import { uniq, includes, toLower } from "lodash";
import NiceModal, { useModal } from "@ebay/nice-modal-react";
import { toast } from "react-toastify";
import GlobalAppContext from "../utils/GlobalAppContext";
import NamePill from "./NamePill";
import {
  getTrackName,
  getArtistName,
  getRecordingMBID,
  getRecordingMSID,
} from "../utils/utils";
import SearchDropDown from "./SearchDropDown";
import { ToastMsg } from "../notifications/Notifications";

export type PersonalRecommendationModalProps = {
  listenToPersonallyRecommend: Listen;
};

export const maxBlurbContentLength = 280;

/** A note about this modal:
 * We use Bootstrap 3 modals, which work with jQuery and data- attributes
 * In order to show the modal properly, including backdrop and visibility,
 * you'll need dataToggle="modal" and dataTarget="#PersonalRecommendationModal"
 * on the buttons that open this modal as well as data-dismiss="modal"
 * on the buttons that close the modal. Modals won't work (be visible) without it
 * until we move to Bootstrap 5 / Bootstrap React which don't require those attributes.
 */

export default NiceModal.create(
  ({ listenToPersonallyRecommend }: PersonalRecommendationModalProps) => {
    // Use a hook to manage the modal state
    const modal = useModal();
    const [users, setUsers] = React.useState<string[]>([]);
    const [followers, setFollowers] = React.useState<string[]>([]);
    const [suggestions, setSuggestions] = React.useState<string[]>([]);
    const [blurbContent, setBlurbContent] = React.useState("");

    const { APIService, currentUser } = React.useContext(GlobalAppContext);
    const { name: currentUserName } = currentUser;

    const handleError = React.useCallback(
      (error: string | Error, title?: string): void => {
        if (!error) {
          return;
        }
        toast.error(
          <ToastMsg
            title={title || "Error"}
            message={typeof error === "object" ? error.message : error}
          />,
          { toastId: "recommended-track-error" }
        );
      },
      []
    );

    /* On load, get the current user's followers */
    React.useEffect(() => {
      APIService.getFollowersOfUser(currentUserName)
        .then((response) => {
          setFollowers(response.followers);
        })
        .catch((error) => {
          handleError(error, "Error while fetching followers");
        });
    }, [currentUserName, setFollowers]);

    const handleBlurbInputChange = React.useCallback(
      (event: React.ChangeEvent<HTMLTextAreaElement>) => {
        event.preventDefault();
        const input = event.target.value.replace(/\s\s+/g, " "); // remove line breaks and excessive spaces
        if (input.length <= maxBlurbContentLength) {
          setBlurbContent(input);
        }
      },
      []
    );

    const addUser = (user: string) => {
      setUsers((prevUsers) => uniq([...prevUsers, user]));
      setSuggestions([]);
    };

    const removeUser = (user: string) => {
      setUsers((prevUsers) => prevUsers.filter((element) => element !== user));
    };

    const searchUsers = React.useCallback(
      (event: React.ChangeEvent<HTMLInputElement>) => {
        if (event?.target?.value) {
          const newSuggestions = followers.filter((username) =>
            includes(toLower(username), toLower(event.target.value))
          );
          setSuggestions(newSuggestions);
        } else {
          setSuggestions([]);
        }
      },
      [followers]
    );

    const closeModal = () => {
      modal.hide();
      setTimeout(modal.remove, 200);
    };

    const submitPersonalRecommendation = React.useCallback(
      async (event: React.MouseEvent<HTMLButtonElement>) => {
        event.preventDefault();
        if (currentUser?.auth_token) {
          const metadata: UserTrackPersonalRecommendationMetadata = {
            users,
            blurb_content: blurbContent,
          };

          const recording_mbid = getRecordingMBID(listenToPersonallyRecommend);
          if (recording_mbid) {
            metadata.recording_mbid = recording_mbid;
          }

          const recording_msid = getRecordingMSID(listenToPersonallyRecommend);
          if (recording_msid) {
            metadata.recording_msid = recording_msid;
          }

          try {
            const status = await APIService.submitPersonalRecommendation(
              currentUser.auth_token,
              currentUser.name,
              metadata
            );
            if (status === 200) {
              toast.success(
                <ToastMsg
                  title={`You recommended this track to ${users.length} user${
                    users.length > 1 ? "s" : ""
                  }`}
                  message={`${getArtistName(
                    listenToPersonallyRecommend
                  )} - ${getTrackName(listenToPersonallyRecommend)}`}
                />,
                { toastId: "recommended-track-success" }
              );
              closeModal();
            }
          } catch (error) {
            handleError(error, "Error while recommending a track");
          }
        }
      },
      [listenToPersonallyRecommend, blurbContent, users]
    );

    const {
      track_name,
      artist_name,
    } = listenToPersonallyRecommend.track_metadata;

    return (
      <div
        className={`modal fade ${modal.visible ? "in" : ""}`}
        id="PersonalRecommendationModal"
        tabIndex={-1}
        role="dialog"
        aria-labelledby="PersonalRecommendationModalLabel"
        data-backdrop="static"
      >
        <div className="modal-dialog" role="document">
          <form className="modal-content">
            <div className="modal-header">
              <button
                type="button"
                className="close"
                data-dismiss="modal"
                aria-label="Close"
                onClick={closeModal}
              >
                <span aria-hidden="true">&times;</span>
              </button>
              <h4 className="modal-title" id="PersonalRecommendationModalLabel">
                Recommend <b>{track_name}</b>
              </h4>
            </div>
            <div className="modal-body">
              {users.map((user) => {
                return (
                  <NamePill
                    title={user}
                    // eslint-disable-next-line react/jsx-no-bind
                    closeAction={removeUser.bind(this, user)}
                  />
                );
              })}
              <input
                type="text"
                className="form-control"
                onChange={searchUsers}
                placeholder="Add followers*"
              />
              <SearchDropDown suggestions={suggestions} action={addUser} />
              <p>Leave a message (optional)</p>
              <div className="form-group">
                <textarea
                  className="form-control"
                  id="blurb-content"
                  placeholder="You will love this song because..."
                  value={blurbContent}
                  name="blurb-content"
                  rows={4}
                  style={{ resize: "vertical" }}
                  onChange={handleBlurbInputChange}
                />
              </div>
              <small className="character-count">
                {blurbContent.length} / {maxBlurbContentLength}
                <br />
                *Can’t find a user? Make sure they are following you, and then
                try again.
              </small>
            </div>
            <div className="modal-footer">
              <button
                type="button"
                className="btn btn-default"
                data-dismiss="modal"
                onClick={closeModal}
              >
                Cancel
              </button>
              <button
                type="submit"
                className="btn btn-success"
                data-dismiss="modal"
                disabled={users.length === 0}
                onClick={submitPersonalRecommendation}
              >
                Send Recommendation
              </button>
            </div>
          </form>
        </div>
      </div>
    );
  }
);
