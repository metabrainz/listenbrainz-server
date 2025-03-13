/* eslint-disable jsx-a11y/anchor-is-valid,camelcase */

import * as React from "react";

import { get, isInteger } from "lodash";
import { toast } from "react-toastify";
import { useLocation, useParams, useSearchParams } from "react-router-dom";

import { Helmet } from "react-helmet";
import { useQuery } from "@tanstack/react-query";
import GlobalAppContext from "../../utils/GlobalAppContext";
import Loader from "../../components/Loader";
import {
  fullLocalizedDateFromTimestampOrISODate,
  getArtistName,
  getObjectForURLSearchParams,
  getRecordingMBID,
  getTrackName,
  preciseTimestamp,
} from "../../utils/utils";
import ListenCard from "../../common/listens/ListenCard";
import RecommendationFeedbackComponent from "../../common/listens/RecommendationFeedbackComponent";
import { ToastMsg } from "../../notifications/Notifications";
import { RouteQuery } from "../../utils/Loader";
import { useBrainzPlayerDispatch } from "../../common/brainzplayer/BrainzPlayerContext";
import Pagination from "../../common/Pagination";

export type RecommendationsProps = {
  recommendations?: Array<Recommendation>;
  user?: ListenBrainzUser;
  errorMsg?: string;
  lastUpdated?: string;
};

type RecommendationsLoaderData = RecommendationsProps;

export interface RecommendationsState {
  currentRecommendation?: Recommendation;
  recommendations: Array<Recommendation>;
  loading: boolean;
  currRecPage?: number;
  totalRecPages: number;
  recommendationFeedbackMap: RecommendationFeedbackMap;
}

export default function Recommendations() {
  const expectedRecommendationsPerPage = 25;

  // Context
  const { APIService, currentUser } = React.useContext(GlobalAppContext);
  const dispatch = useBrainzPlayerDispatch();

  // Loader Data
  const location = useLocation();
  const params = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const searchParamsObject = getObjectForURLSearchParams(searchParams);
  const { data: props } = useQuery<RecommendationsLoaderData>(
    RouteQuery(
      ["recommendation", params, searchParamsObject],
      location.pathname
    )
  );

  const { recommendations: recommendationProps, errorMsg, user, lastUpdated } =
    props || {};

  // State
  const [recommendations, setRecommendations] = React.useState<
    Array<Recommendation>
  >(recommendationProps?.slice(0, expectedRecommendationsPerPage) || []);
  const [loading, setLoading] = React.useState<boolean>(false);
  const [currRecPage, setCurrRecPage] = React.useState<number>(1);
  const [
    recommendationFeedbackMap,
    setRecommendationFeedbackMap,
  ] = React.useState<RecommendationFeedbackMap>({});

  // Ref
  const recommendationsTableRef = React.useRef<HTMLDivElement>(null);
  const totalRecPages = recommendationProps
    ? Math.ceil(recommendationProps.length / expectedRecommendationsPerPage)
    : 0;

  // Functions
  const getFeedback = async () => {
    const recordings: string[] = [];

    if (recommendations && recommendations.length > 0 && user?.name) {
      recommendations.forEach((recommendation) => {
        const recordingMbid = getRecordingMBID(recommendation);
        if (recordingMbid) {
          recordings.push(recordingMbid);
        }
      });
      try {
        const data = await APIService.getFeedbackForUserForRecommendations(
          user?.name,
          recordings.join(",")
        );
        return data.feedback;
      } catch (error) {
        toast.error(
          <ToastMsg
            title="We could not load love/hate feedback"
            message={typeof error === "object" ? error.message : error}
          />,
          { toastId: "load-feedback-error" }
        );
      }
    }
    return [];
  };

  const loadFeedback = async () => {
    const feedback = await getFeedback();
    if (!feedback) {
      return;
    }
    const newRecommendationFeedbackMap: RecommendationFeedbackMap = {};
    feedback.forEach((fb: RecommendationFeedbackResponse) => {
      newRecommendationFeedbackMap[fb.recording_mbid] = fb.rating;
    });
    setRecommendationFeedbackMap(newRecommendationFeedbackMap);
  };

  const updateFeedback = (
    recordingMbid: string,
    rating: ListenFeedBack | RecommendationFeedBack | null
  ) => {
    setRecommendationFeedbackMap((state) => ({
      ...state,
      [recordingMbid]: rating as RecommendationFeedBack,
    }));
  };

  const getFeedbackForRecordingMbid = (
    recordingMbid?: string | null
  ): RecommendationFeedBack | null => {
    return recordingMbid
      ? get(recommendationFeedbackMap, recordingMbid, null)
      : null;
  };

  const afterRecommendationsDisplay = () => {
    if (currentUser?.name === user?.name) {
      loadFeedback();
    }
    if (recommendationsTableRef?.current) {
      recommendationsTableRef.current.scrollIntoView({ behavior: "smooth" });
    }
    setLoading(false);
  };

  const handleClickPrevious = () => {
    if (currRecPage && currRecPage > 1) {
      setLoading(true);
      const offset = (currRecPage - 1) * expectedRecommendationsPerPage;
      const updatedRecPage = currRecPage - 1;
      setCurrRecPage(updatedRecPage);
      setRecommendations(
        recommendationProps?.slice(
          offset - expectedRecommendationsPerPage,
          offset
        ) || []
      );
      afterRecommendationsDisplay();
      window.history.pushState(null, "", `?page=${updatedRecPage}`);
    }
  };

  const handleClickNext = () => {
    if (currRecPage && currRecPage < totalRecPages) {
      setLoading(true);
      const offset = currRecPage * expectedRecommendationsPerPage;
      const updatedRecPage = currRecPage + 1;
      setCurrRecPage(updatedRecPage);
      setRecommendations(
        recommendationProps?.slice(
          offset,
          offset + expectedRecommendationsPerPage
        ) || []
      );
      afterRecommendationsDisplay();
      window.history.pushState(null, "", `?page=${updatedRecPage}`);
    }
  };

  // Effects
  React.useEffect(() => {
    if (currentUser?.name === user?.name) {
      loadFeedback();
    }
    window.history.replaceState(null, "", `?page=${currRecPage}`);
  }, [currentUser]);

  React.useEffect(() => {
    dispatch({
      type: "SET_AMBIENT_QUEUE",
      data: recommendations,
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [recommendations]);

  return (
    <div role="main" data-testid="recommendations">
      <Helmet>
        <title>{`User - ${user?.name}`}</title>
      </Helmet>
      {errorMsg ? (
        <div>
          <h2>Error</h2>
          <p>{errorMsg}</p>
        </div>
      ) : (
        <>
          <div
            style={{
              marginTop: "20px",
            }}
          >
            <p>
              Your raw tracks playlist was last updated on <b>{lastUpdated}</b>.
            </p>
          </div>
          <div className="row">
            <div className="col-md-8">
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
                  id="recommendations"
                  data-testid="recommendations-table"
                  ref={recommendationsTableRef}
                  style={{ opacity: loading ? "0.4" : "1" }}
                >
                  {recommendations.map((recommendation) => {
                    const recordingMBID = getRecordingMBID(recommendation);
                    const recommendationFeedbackComponent = (
                      <RecommendationFeedbackComponent
                        updateFeedbackCallback={updateFeedback}
                        listen={recommendation}
                        currentFeedback={getFeedbackForRecordingMbid(
                          recordingMBID
                        )}
                      />
                    );
                    // Backwards compatible support for various timestamp property names
                    let discoveryTimestamp: string | number | undefined | null =
                      recommendation.latest_listened_at;
                    if (!discoveryTimestamp) {
                      discoveryTimestamp = recommendation.listened_at_iso;
                    }
                    if (
                      !discoveryTimestamp &&
                      isInteger(recommendation.listened_at)
                    ) {
                      // Transfrom unix timestamp in JS milliseconds timestamp
                      discoveryTimestamp = recommendation.listened_at * 1000;
                    }
                    const customTimestamp = discoveryTimestamp ? (
                      <span
                        className="listen-time"
                        title={fullLocalizedDateFromTimestampOrISODate(
                          discoveryTimestamp
                        )}
                      >
                        Last listened at
                        <br />
                        {preciseTimestamp(discoveryTimestamp)}
                      </span>
                    ) : (
                      <span className="listen-time">Not listened to yet</span>
                    );
                    return (
                      <ListenCard
                        key={`${getTrackName(recommendation)}-${getArtistName(
                          recommendation
                        )}`}
                        customTimestamp={customTimestamp}
                        showTimestamp
                        showUsername={false}
                        feedbackComponent={recommendationFeedbackComponent}
                        listen={recommendation}
                      />
                    );
                  })}
                </div>
                <Pagination
                  currentPageNo={currRecPage}
                  totalPageCount={totalRecPages}
                  handleClickPrevious={handleClickPrevious}
                  handleClickNext={handleClickNext}
                />
              </div>

              <br />
            </div>
          </div>
        </>
      )}
    </div>
  );
}
