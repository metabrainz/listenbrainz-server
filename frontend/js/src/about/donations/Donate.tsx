import { faCheck } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import * as React from "react";
import { COLOR_LB_GREEN } from "../../utils/constants";
import Blob from "../../home/Blob";

export default function Data() {
  return (
    <div id="donations-page">
      <Blob width={250} height={250} randomness={1.5} className="blob" />
      <Blob
        width={250}
        height={250}
        randomness={1.1}
        className="blob"
        style={{ top: "45%", right: "15%" }}
      />
      <div>
        <div className="donations-page-header">
          <h1>
            Money can&apos;t buy happiness, but it can buy
            <br />
            <span style={{ fontWeight: 600 }}>LISTENBRAINZ HOSTING</span>
          </h1>
          <p>
            ListenBrainz is a free, open-source and non-profit project.
            <br />
            If you enjoy it, you can help us survive and thrive with your
            donations.
            <br />
            At our scale, every contribution matters.
          </p>
        </div>
        <div id="donations-tiers">
          <div className="tier card text-center">
            <div>
              <h2>
                <b>Free for everyone</b>
              </h2>
            </div>
            <div className="perk">
              <FontAwesomeIcon icon={faCheck} color={COLOR_LB_GREEN} />{" "}
              <b>All website features, for free, forever</b>
            </div>
          </div>
          <div className="tier card">
            <div className="tier-heading">
              <h2>
                <b>5$</b>
                <br />
                donation
              </h2>
              <br />
              <button type="button" className="btn btn-primary">
                Donate
              </button>
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
                Add a special effect to your username on the website
              </small>
            </div>
            <div className="perk">
              <FontAwesomeIcon icon={faCheck} color={COLOR_LB_GREEN} />{" "}
              <b>Our eternal gratitude</b>
            </div>
          </div>
          <div className="tier card">
            <div className="tier-heading">
              <h2>
                <b>20$</b>
                <br />
                donation
              </h2>
              <br />
              <button type="button" className="btn btn-primary">
                Donate
              </button>
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
                Add a special effect to your username on the website
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
              <h2>
                <b>50$</b>
                <br />
                donation
              </h2>
              <br />
              <button type="button" className="btn btn-primary">
                Donate
              </button>
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
                Add a special effect to your username on the website
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
              <small>Or maybe show her you haven&apos;t changed</small>
            </div>
            <div className="perk">
              <FontAwesomeIcon icon={faCheck} color={COLOR_LB_GREEN} />
              &nbsp;
              <b>Bragging rights</b>
              <br />
              <small>
                When we have taken over the world, you can proudly say
                <i>
                  &ldquo;I helped our music recommendation overlords get to
                  where they are today&rdquo;
                </i>
              </small>
            </div>
          </div>
        </div>
        <div className="donations-page-footer">
          <h3>Jokes aside</h3>
          <p>
            Join our music network, where <b>you aren&apos;t the product</b> and
            your personal data isn&apos;t the price you pay.
            <br />
            We believe everyone should have access to all features —no paywalls,
            no “Pro++” features.
            <br />
            <b>All features are free for everyone.</b>
            <br />
            <br />
            While it takes real-world money to keep us going, all our data is
            open-srouce and free for everyone.
            <br />
            Commercial users are expected to contribute back and support us, but
            it&apos;s not enough to fund the new features you want.
            <br />
            <br />
            By donating —either once or regularly— you&apos;ll join thousands of
            music lovers in helping us build an honest, unbiased and
            community-driven space for music discovery.
          </p>
        </div>
      </div>
      <div className="grey-wedge" />
    </div>
  );
}
