import { useQuery } from "@tanstack/react-query";
import React from "react";
import { useLocation } from "react-router";
import { RouteQuery } from "../../utils/Loader";
import {
  fullLocalizedDateFromTimestampOrISODate,
  formatSecondsDuration,
} from "../../utils/utils";

import UserEvolutionChart, { UserEvolutionData } from "./UserEvolutionChart";

type CurrentStatusLoaderData = {
  listenCount: number;
  listenCountsPerDay: {
    date: string;
    listenCount: number;
    label: string;
  }[];
  userCount: number;
  serviceStatus: {
    time: number;
    dump_age: number;
    stats_age: number;
    sitewide_stats_age: number;
    incoming_listen_count: number;
  };
  userCountEvolution: UserEvolutionData[];
};

export default function CurrentStatus() {
  const location = useLocation();
  const { data } = useQuery<CurrentStatusLoaderData>(
    RouteQuery(["current-status"], location.pathname)
  );
  const { userCount, listenCount, listenCountsPerDay, serviceStatus } =
    data || {};
  return (
    <>
      <h2 className="page-title">Current status</h2>

      <div className="row">
        <div className="col">
          <h3>ListenBrainz Stats</h3>
          <h4>User count</h4>
          <UserEvolutionChart
            userCountEvolution={data?.userCountEvolution || []}
          />
          <table className="table table-border table-sm table-striped">
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

          <h3>Current Service Status</h3>
          <table className="table table-border table-sm table-striped">
            <thead>
              <tr>
                <th>Field</th>
                <th>Value</th>
              </tr>
            </thead>
            <tbody>
              {serviceStatus && (
                <tr>
                  <td>Last Updated</td>
                  <td>
                    {fullLocalizedDateFromTimestampOrISODate(
                      new Date(serviceStatus.time * 1000)
                    )}
                  </td>
                </tr>
              )}
              {serviceStatus && (
                <tr>
                  <td>Database Dump Age</td>
                  <td>{formatSecondsDuration(serviceStatus.dump_age)}</td>
                </tr>
              )}
              {serviceStatus && (
                <tr>
                  <td>Stats Age</td>
                  <td>{formatSecondsDuration(serviceStatus.stats_age)}</td>
                </tr>
              )}
              {serviceStatus && (
                <tr>
                  <td>Sitewide Stats Age</td>
                  <td>
                    {formatSecondsDuration(serviceStatus.sitewide_stats_age)}
                  </td>
                </tr>
              )}
              {serviceStatus && (
                <tr>
                  <td>Incoming Listen Count</td>
                  <td>
                    {new Intl.NumberFormat().format(
                      serviceStatus.incoming_listen_count
                    )}{" "}
                    listens
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}
