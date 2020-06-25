import * as React from "react";

import Card from "../components/Card";
import LineDualTone from "./LineDualTone";

const data = [
  {
    id: "Last Week",
    data: [
      {
        x: 1590364800,
        y: 5,
      },
      {
        x: 1590451200,
        y: 25,
      },
      {
        x: 1590537600,
        y: 53,
      },
      {
        x: 1590624000,
        y: 21,
      },
      {
        x: 1590710400,
        y: 8,
      },
      {
        x: 1590796800,
        y: 11,
      },
      {
        x: 1590883200,
        y: 11,
      },
    ],
  },
  {
    id: "This Week",
    data: [
      {
        x: 1590364800,
        y: 22,
      },
      {
        x: 1590451200,
        y: 10,
      },
      {
        x: 1590537600,
        y: 18,
      },
      {
        x: 1590624000,
        y: 35,
      },
      {
        x: 1590710400,
        y: 30,
      },
      {
        x: 1590796800,
        y: 3,
      },
      {
        x: 1590883200,
        y: 0,
      },
    ],
  },
];

export default class UserListeningActivity extends React.Component {
  render() {
    return (
      <div>
        <div className="col-md-8" style={{ height: "20em" }}>
          <Card>
            <LineDualTone data={data} />
          </Card>
        </div>
        <div className="col-md-4" style={{ height: "20em" }}>
          <Card style={{ display: "flex", alignItems: "center" }}>
            <table
              style={{ height: "50%", width: "100%", tableLayout: "fixed" }}
            >
              <tbody>
                <tr>
                  <td
                    style={{
                      width: "30%",
                      textAlign: "end",
                      fontSize: 30,
                      fontWeight: "bold",
                    }}
                  >
                    118
                  </td>
                  <td>
                    <span style={{ fontSize: 24 }}>&nbsp;Listens</span>
                  </td>
                </tr>
                <tr>
                  <td
                    style={{
                      width: "30%",
                      textAlign: "end",
                      fontSize: 30,
                      fontWeight: "bold",
                    }}
                  >
                    17
                  </td>
                  <td>
                    <span style={{ fontSize: 24 }}>&nbsp;Listens per day</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </Card>
        </div>
      </div>
    );
  }
}
