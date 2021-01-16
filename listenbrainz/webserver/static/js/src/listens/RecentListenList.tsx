import * as React from 'react'
import ListenCard from './ListenCard';

export type RecentListenListProps = {
    tableref: () => React.RefObject<HTMLTableElement>;
    loading: boolean;
    listens: Array<Listen>;
    currentUser: ListenBrainzUser | undefined;
    isCurrentUser: boolean;
    apiUrl: string;
    mode: ListensListMode;
    getFeedbackForRecordingMsid: (recordingMsid?: string | null | undefined) => ListenFeedBack;
    playListen: (listen: Listen) => void;
    removeListenFromListenList: (listen: Listen) => void;
    updateFeedback: (recordingMsid: string, score: ListenFeedBack) => void;
    newAlert: (type: AlertType, title: string, message: string | JSX.Element) => void;
    isCurrentListen: (listen: Listen) => boolean;
}

const RecentListenList = ({
    tableref, loading, listens,
    currentUser, isCurrentUser,
    apiUrl, mode, getFeedbackForRecordingMsid,
    playListen, removeListenFromListenList,
    updateFeedback, newAlert,
    isCurrentListen
}: RecentListenListProps) => {

    return (
        <div
            id="listens"
            ref={tableref()}
            style={{ opacity: loading ? "0.4" : "1" }}
        >
            {listens
                .sort((a, b) => {
                    if (a.playing_now) {
                        return -1;
                    }
                    if (b.playing_now) {
                        return 1;
                    }
                    return 0;
                })
                .map((listen) => {
                    return (
                        <ListenCard
                            key={`${listen.listened_at}-${listen.track_metadata?.track_name}-${listen.track_metadata?.additional_info?.recording_msid}-${listen.user_name}`}
                            currentUser={currentUser}
                            isCurrentUser={isCurrentUser}
                            apiUrl={apiUrl}
                            listen={listen}
                            mode={mode}
                            currentFeedback={getFeedbackForRecordingMsid(
                                listen.track_metadata?.additional_info
                                    ?.recording_msid
                            )}
                            playListen={playListen}
                            removeListenFromListenList={
                                removeListenFromListenList
                            }
                            updateFeedback={updateFeedback}
                            newAlert={newAlert}
                            className={`${isCurrentListen(listen)
                                ? " current-listen"
                                : ""
                                }${listen.playing_now ? " playing-now" : ""}`}
                        />
                    );
                })}
        </div>
    )

}

export default RecentListenList;