import { faCheck } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import * as React from "react";
import { COLOR_LB_GREEN } from "../../utils/constants";

export default function Data() {
  return (
    <div id="donations-page">
      <div className="">
        <h1>Money can’t buy happiness, but it can buy LISTENBRAINZ HOSTING</h1>
        <p>
          ListenBrainz is open-source and non-profit, and you can help us
          survive and thrive with repeating or one-time donations.
        </p>
        <div id="donations-tiers">
          <div className="tier card">
            <div className="tier-heading">
              <h3>Free</h3>
            </div>
            <div className="perk">
              <FontAwesomeIcon icon={faCheck} color={COLOR_LB_GREEN} />{" "}
              <b>All website features, for free, forever</b>
            </div>
          </div>
          <div className="tier card">
            <div className="tier-heading">
              <h3>10$ donation</h3>
              <br />
              <button type="button">Donate here</button>
            </div>
            <div className="perk">
              <FontAwesomeIcon icon={faCheck} color={COLOR_LB_GREEN} />{" "}
              <b>All website features, for free, forever</b>
            </div>

            <div className="perk">
              <FontAwesomeIcon icon={faCheck} color={COLOR_LB_GREEN} />{" "}
              <b>User flair</b>
              <br />
              <small>
                Your username will appear with a special effect on the website
                for everyone to see
              </small>
            </div>
            <div className="perk">
              <FontAwesomeIcon icon={faCheck} color={COLOR_LB_GREEN} />{" "}
              <b>Our eternal gratitude</b>
            </div>
            <div className="perk">
              <FontAwesomeIcon icon={faCheck} color={COLOR_LB_GREEN} />
              &nbsp;
              <b>Inner sense of peace and accomplishment</b>
            </div>
          </div>
          <div className="tier card">
            <div className="tier-heading">
              <h3>50$ donation</h3>
              <br />
              <button type="button">Donate here</button>
            </div>
            <div className="perk">
              <FontAwesomeIcon icon={faCheck} color={COLOR_LB_GREEN} />{" "}
              <b>All website features, for free, forever</b>
            </div>

            <div className="perk">
              <FontAwesomeIcon icon={faCheck} color={COLOR_LB_GREEN} />{" "}
              <b>User flair</b>
              <br />
              <small>
                Your username will appear with a special effect on the website
                for everyone to see
              </small>
            </div>
            <div className="perk">
              <FontAwesomeIcon icon={faCheck} color={COLOR_LB_GREEN} />{" "}
              <b>Our eternal gratitude</b>
            </div>
            <div className="perk">
              <FontAwesomeIcon icon={faCheck} color={COLOR_LB_GREEN} />
              &nbsp;
              <b>Inner sense of peace and accomplishment</b>
            </div>
            <div className="perk">
              <FontAwesomeIcon icon={faCheck} color={COLOR_LB_GREEN} />
              &nbsp;
              <b>Make your momma proud</b>
              <br />
              <small>
                Or maybe show her you haven&apos;t changed, depending.
              </small>
            </div>
            <div className="perk">
              <FontAwesomeIcon icon={faCheck} color={COLOR_LB_GREEN} />
              &nbsp;
              <b>Bragging rights</b>
              <br />
              <small>
                When we have taken over the world, you&apos;ll be able to
                proudly say
                <i>
                  &ldquo;I helped our music recommendation overlords get to
                  where they are today&rdquo;
                </i>
              </small>
            </div>
          </div>
        </div>
        <hr />
        <h3>Jokes aside</h3>
        <p>
          We believe in creating a free service for all where you do not pay
          with your personal information and where <b>you</b> do not
          become the product like so many other online services.
          <br />
          Similarly, we want all features to ba available to everyone, and steer
          away from a pay-to-play, &quot;ListenBrainz Pro++&quot; model.
        </p>
        <p>
          Of course, hosting and developing such a service costs money in the
          real world, and we are not exempt from that reality. All the
          information (listening history, popularity, etc.) is available
          publicly and for free to anyone, but commercial entities are expected to support us
          financially. That is not quite enough to pay for everything or to have
          the resources we need to create the features you request.
        </p>
        <p>
          Please consider joining thousands of passionate contributors with a
          one-time or regular donation. You will be helping this ecosystem
          grow into an honest archipelago of music lovers.
        </p>
      </div>
      <div
        style={{
          height: "65%",
          bottom: 0,
          clipPath: "polygon(0 25%, 100% 0, 100% 100%, 0% 100%)",
          background: "#e9e9e9",
          position: "absolute",
          left: 0,
          width: "100%",
          zIndex: 0,
        }}
      />
    </div>
  );
}
