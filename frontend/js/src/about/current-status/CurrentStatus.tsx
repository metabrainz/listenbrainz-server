import { useQuery } from "@tanstack/react-query";
import React from "react";
import { useLocation } from "react-router-dom";
import { RouteQuery } from "../../utils/Loader";

type CurrentStatusLoaderData = {
  listenCount: number;
  listenCountsPerDay: {
    date: string;
    listenCount: number;
    label: string;
  }[];
  userCount: number;
  load: string;
};

export default function CurrentStatus() {
  const location = useLocation();
  const { data } = useQuery<CurrentStatusLoaderData>(
    RouteQuery(["current-status"], location.pathname)
  );
  const { userCount, listenCount, listenCountsPerDay, load } = data || {};
  return (
    <>
      <h2 className="page-title">Current status</h2>

      <div className="row">
        <div className="col-md-7 col-lg-8">
          <h3>ListenBrainz Stats</h3>
          <table className="table table-border table-condensed table-striped">
            <thead>
              <tr>
                <th>Description</th>
                <th>Number</th>
              </tr>
            </thead>
            <tbody>
              {userCount && (
                <tr>
                  <td>Number of users</td>
                  <td>{userCount}</td>
                </tr>
              )}
              {listenCount && (
                <tr>
                  <td>Number of listens</td>
                  <td>{listenCount}</td>
                </tr>
              )}
              {listenCountsPerDay &&
                listenCountsPerDay.map((listenCountData, index) => (
                  <tr key={`listen-count-${listenCountData.date}`}>
                    <td>
                      Number of listens submitted {listenCountData.label} (
                      {listenCountData.date})
                    </td>
                    <td>{listenCountData.listenCount}</td>
                  </tr>
                ))}
            </tbody>
          </table>

          <p>
            If you are curious about the state of our Listen ingestion
            pipelines, you can create yourself a free account on our{" "}
            <a href="https://stats.metabrainz.org">
              infrastructure statistics site
            </a>
            . In particular, the{" "}
            <a href="https://stats.metabrainz.org/d/000000059/rabbitmq?orgId=1&refresh=1m&var-queue_vhost=%2Flistenbrainz">
              RabbitMQ ListenBrainz view
            </a>{" "}
            shows how many listens we are currently processing, and the number
            of incoming listens currently queued for processing.
          </p>

          <p>
            Something isn&apos;t updating? Stay calm and check the{" "}
            <a href="https://listenbrainz.readthedocs.io/en/latest/general/data-update-intervals.html">
              Expected Data Update Intervals
            </a>{" "}
            doc.
          </p>

          <h3>load average</h3>

          <p>Current server load average</p>
          <div className="well">{load}</div>
        </div>

        <div className="col-md-5 col-lg-4">
          <p style={{ textAlign: "center" }}>
            <img
              style={{ borderRadius: "15px" }}
              src="/static/img/selfie.jpg"
              width="250"
              alt="Selfie"
            />
          </p>

          <p style={{ textAlign: "center" }}>
            Our server doesn&apos;t have a selfie. :( <br />
            Have a monkey selfie instead!
          </p>
        </div>
      </div>
    </>
  );
}
