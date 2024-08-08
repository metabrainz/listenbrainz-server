import React, { useCallback, useContext, useState } from "react";
import { Helmet } from "react-helmet";
import GlobalAppContext from "../../utils/GlobalAppContext";
import { useBrainzPlayerDispatch } from "../../common/brainzplayer/BrainzPlayerContext";

const totallyInnocentListen: Listen = {
  listened_at: 1654079332,
  track_metadata: {
    additional_info: {
      youtube_id: "dQw4w9WgXcQ",
      recording_mbid: "8f3471b5-7e6a-48da-86a9-c1c07a0f47ae",
      recording_msid: "790b2544-5675-4f2b-b714-6b373fca0c80",
      release_mbid: "bf9e91ea-8029-4a04-a26a-224e00a83266",
    },
    mbid_mapping: {
      artist_mbids: ["db92a151-1ac2-438b-bc43-b82e149ddd50"],
      caa_id: 30721131344,
      caa_release_mbid: "bf9e91ea-8029-4a04-a26a-224e00a83266",
      recording_mbid: "8f3471b5-7e6a-48da-86a9-c1c07a0f47ae",
      release_mbid: "bf9e91ea-8029-4a04-a26a-224e00a83266",
    },
    artist_name: "Rick Astley",
    release_name: "Whenever You Need Somebody",
    track_name: "Never Gonna Give You Up",
  },
};

function AIBrainzHeader() {
  const dispatch = useBrainzPlayerDispatch();
  React.useEffect(() => {
    dispatch({ type: "SET_AMBIENT_QUEUE", data: [totallyInnocentListen] });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [totallyInnocentListen]);
  return (
    <Helmet>
      <title>AIBrainz</title>
      <style type="text/css">
        {`#AIBrainz {
          text-align: center;
        }
        
        .toggle {
          cursor: pointer;
          display: inline-block;
        }

        .toggle-switch {
          display: inline-block;
          background: #ccc;
          border-radius: 16px;
          width: 42px;
          height: 18px;
          position: relative;
          vertical-align: middle;
          transition: background 0.25s;
        }
        .toggle-switch:before, .toggle-switch:after {
          content: "";
        }
        .toggle-switch:before {
          display: block;
          background: linear-gradient(to bottom, #fff 0%, #eee 100%);
          border-radius: 50%;
          box-shadow: 0 0 0 1px rgba(0, 0, 0, 0.25);
          width: 19px;
          height: 19px;
          position: absolute;
          top: 0px;
          left: 0px;
          transition: left 0.25s;
        }
        .toggle:hover .toggle-switch:before {
          background: linear-gradient(to bottom, #fff 0%, #fff 100%);
          box-shadow: 0 0 0 1px rgba(0, 0, 0, 0.5);
        }
        .toggle-checkbox:checked + .toggle-switch {
          background: #353070;
        }
        .toggle-checkbox:checked + .toggle-switch:before {
          left: 23px;
        }

        .toggle-checkbox {
          position: absolute;
          visibility: hidden;
        }

        .toggle-label {
          margin-left: 5px;
          position: relative;
          top: 2px;
        }
        .big-ai-button {
          margin-top:1.5em;
          margin-bottom:1.5em;
          width: 200px;
          min-height: 170px;
          background-color: #353070;
          color: white;
          padding: 1em;
          border-radius: 15px;
          font-size: 2em;
          text-align: center;
        }
        .big-ai-button.disabled{
          cursor: not-allowed;
        }
        .settings{
          margin: 1.4em auto
        }
        .settings td {
          text-align: initial;
          padding: 0.2em 0.5em;
        }
        .confirmation {
          max-width: 610px;
          margin: auto;
        }
        .confirmation > input{
          flex:0;
          margin-right: 1em;
        }`}
      </style>
      <script src="https://cdn.jsdelivr.net/npm/canvas-confetti@1.6.0/dist/confetti.browser.min.js" />
      <script type="text/javascript">
        {`var duration = 15 * 1000;
      var defaults = { startVelocity: 30, spread: 360, ticks: 60, zIndex: 0 };
      
      function randomInRange(min, max) {
        return Math.random() * (max - min) + min;
      }
      
      
      window.addEventListener("message", (event)=>{
        if (event.origin !== window.location.origin) {
          // Received postMessage from different origin, ignoring it
          return;
        }
        const { aibrainz } = event.data;
        if(aibrainz !== 'confetti-cannon') {
          return;
        }
        var animationEnd = Date.now() + duration;
        var interval = setInterval(function() {
          var timeLeft = animationEnd - Date.now();
        
          if (timeLeft <= 0) {
            return clearInterval(interval);
          }
        
          var particleCount = 50 * (timeLeft / duration);
          // since particles fall down, start a bit higher than random
          confetti(Object.assign({}, defaults, { particleCount, origin: { x: randomInRange(0.1, 0.3), y: Math.random() - 0.2 } }));
          confetti(Object.assign({}, defaults, { particleCount, origin: { x: randomInRange(0.7, 0.9), y: Math.random() - 0.2 } }));
        }, 250);
      });`}
      </script>
    </Helmet>
  );
}

type AIBrainzComponentProps = {};

export default function AIBrainzComponent(props: AIBrainzComponentProps) {
  const { APIService } = useContext(GlobalAppContext);
  const [submitted, setSubmitted] = useState(false);
  const [inputs, setInputs] = useState({
    checkbox1: true,
    checkbox2: false,
    checkbox3: true,
    checkbox4: true,
    checkbox5: true,
    checkbox6: false,
    checkbox7: true,
    checkbox8: false,
    checkbox9: false,
  });
  const isConfirmed = Boolean(inputs.checkbox9);
  const onConfirm = useCallback(() => {
    if (!isConfirmed) {
      // not confirmed
      return;
    }

    window.postMessage(
      { brainzplayer_event: "play-listen", payload: totallyInnocentListen },
      window.location.origin
    );
    window.postMessage({ aibrainz: "confetti-cannon" }, window.location.origin);
    setSubmitted(true);
    setInputs({
      checkbox1: false,
      checkbox2: false,
      checkbox3: false,
      checkbox4: false,
      checkbox5: false,
      checkbox6: false,
      checkbox7: false,
      checkbox8: false,
      checkbox9: true,
    });
    setTimeout(() => {
      // Jerry-rigged autoplay feature
      window.postMessage(
        { brainzplayer_event: "force-play", payload: totallyInnocentListen },
        window.location.origin
      );
    }, 1000);
  }, [isConfirmed]);

  const onCheckboxChange = (
    checkboxEvent: React.ChangeEvent<HTMLInputElement>
  ) => {
    const { name, checked } = checkboxEvent.target;
    setInputs((prevState) => {
      const stateCopy = { ...prevState };
      // @ts-ignore
      stateCopy[name] = checked;

      return stateCopy;
    });
  };

  return (
    <div id="AIBrainz" role="main">
      <AIBrainzHeader />
      <h3>AIBrainz playlist generator (beta)</h3>
      <br />
      <p style={{ fontWeight: "bold" }}>
        You have 5 free generation tokens remaining.
      </p>
      <br />
      <p>
        Settings
        <br />
        <small>Customize your playlist according to your tastes</small>
      </p>
      {submitted && <p>Never gonna…</p>}
      <table className="settings">
        <tr>
          <td>
            <label className="toggle">
              <input
                className="toggle-checkbox"
                type="checkbox"
                onChange={onCheckboxChange}
                name="checkbox1"
                checked={inputs.checkbox1}
              />
              <div className="toggle-switch" />
              <span className="toggle-label">
                {submitted ? "Give you up" : "Recent only"}
              </span>
            </label>
          </td>
          <td>
            <label className="toggle">
              <input
                className="toggle-checkbox"
                type="checkbox"
                onChange={onCheckboxChange}
                name="checkbox2"
                checked={inputs.checkbox2}
              />
              <div className="toggle-switch" />
              <span className="toggle-label">
                {submitted ? "Let you down" : "Lenticles"}
              </span>
            </label>
          </td>
          <td>
            <label className="toggle">
              <input
                className="toggle-checkbox"
                type="checkbox"
                onChange={onCheckboxChange}
                name="checkbox3"
                checked={inputs.checkbox3}
              />
              <div className="toggle-switch" />
              <span className="toggle-label">
                {submitted ? "Let you down" : "Popular"}
              </span>
            </label>
          </td>
          <td>
            <label className="toggle">
              <input
                className="toggle-checkbox"
                type="checkbox"
                onChange={onCheckboxChange}
                name="checkbox4"
                checked={inputs.checkbox4}
              />
              <div className="toggle-switch" />
              <span className="toggle-label">
                {submitted ? "Desert you" : "Upbeat"}
              </span>
            </label>
          </td>
        </tr>
        <tr>
          <td>
            <label className="toggle">
              <input
                className="toggle-checkbox"
                type="checkbox"
                onChange={onCheckboxChange}
                name="checkbox5"
                checked={inputs.checkbox5}
              />
              <div className="toggle-switch" />
              <span className="toggle-label">
                {submitted ? "Make you cry" : "Personal data"}
              </span>
            </label>
          </td>
          <td>
            <label className="toggle">
              <input
                className="toggle-checkbox"
                type="checkbox"
                onChange={onCheckboxChange}
                name="checkbox6"
                checked={inputs.checkbox6}
              />
              <div className="toggle-switch" />
              <span className="toggle-label">
                {submitted ? "Say goodbye" : "Debug mode"}
              </span>
            </label>
          </td>
          <td>
            <label className="toggle">
              <input
                className="toggle-checkbox"
                type="checkbox"
                onChange={onCheckboxChange}
                name="checkbox7"
                checked={inputs.checkbox7}
              />
              <div className="toggle-switch" />
              <span className="toggle-label">
                {submitted ? "Tell a lie" : "Niche"}
              </span>
            </label>
          </td>
          <td>
            <label className="toggle">
              <input
                className="toggle-checkbox"
                type="checkbox"
                onChange={onCheckboxChange}
                name="checkbox8"
                checked={inputs.checkbox8}
              />
              <div className="toggle-switch" />
              <span className="toggle-label">
                {submitted ? "Hurt you" : "Downbeat"}
              </span>
            </label>
          </td>
        </tr>
      </table>
      <div className="flex confirmation">
        <div>
          <input
            type="checkbox"
            onChange={onCheckboxChange}
            name="checkbox9"
            checked={inputs.checkbox9}
            style={{ marginRight: "20px" }}
          />
          I give my permission for AIBrainz to scan all my apps and devices, for
          music history.
          <br />
          MetaBrainz is committed to open-source and data-privacy, and we will
          delete all personal information as soon as the AI has completed it’s
          playlist generation.
        </div>
      </div>
      {!inputs.checkbox9 && (
        <div className="alert alert-warning" style={{ marginTop: "1em" }}>
          You must accept the permissions above before you can continue
        </div>
      )}
      <button
        className={`big-ai-button ${!inputs.checkbox9 ? "disabled" : ""}`}
        type="button"
        onClick={onConfirm}
      >
        <svg
          width="45"
          height="46"
          viewBox="0 0 45 46"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          <path
            d="M22.5 0.721985C10.1967 0.721985 0.228271 10.6904 0.228271 22.9937C0.228271 35.297 10.1967 45.2654 22.5 45.2654C34.8033 45.2654 44.7717 35.297 44.7717 22.9937C44.7717 10.6904 34.8033 0.721985 22.5 0.721985ZM35.4319 25.5082C35.4319 26.1009 34.947 26.5859 34.3543 26.5859H26.0922V34.848C26.0922 35.4407 25.6072 35.9256 25.0145 35.9256H19.9854C19.3927 35.9256 18.9078 35.4407 18.9078 34.848V26.5859H10.6457C10.053 26.5859 9.56802 26.1009 9.56802 25.5082V20.4791C9.56802 19.8864 10.053 19.4015 10.6457 19.4015H18.9078V11.1394C18.9078 10.5467 19.3927 10.0617 19.9854 10.0617H25.0145C25.6072 10.0617 26.0922 10.5467 26.0922 11.1394V19.4015H34.3543C34.947 19.4015 35.4319 19.8864 35.4319 20.4791V25.5082Z"
            fill="white"
          />
        </svg>
        <div>Generate AI playlist</div>
      </button>
      <p>
        Proudly powered by
        <br />
        <svg
          width="157"
          height="30"
          viewBox="0 0 157 30"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          <g clipPath="url(#clip0_3_261)">
            <path
              d="M13.6522 1.94688L1.95032 8.71355V22.2469L13.6522 29.0136V1.94688Z"
              fill="#1E1E1E"
            />
            <path
              d="M14.6273 1.94688L26.3292 8.71355V22.2469L14.6273 29.0136V1.94688Z"
              fill="#EB743B"
            />
            <path
              d="M48.6602 21.6572H40.7029L39.3182 26.1136H33.1162L41.9414 2.23689H47.4022L56.3054 26.1136H50.0644L48.6602 21.6572ZM42.0974 17.2106H47.2755L44.6816 8.92623L42.0974 17.2106Z"
              fill="#1E1E1E"
            />
            <path
              d="M64.2431 26.1136H58.4507V2.23689H64.2431V26.1136Z"
              fill="#1E1E1E"
            />
            <path
              d="M67.7927 26.1136V7.01222H75.5355C78.2854 7.01222 80.3722 7.46656 81.8155 8.36556C83.2587 9.26456 83.9706 10.5792 83.9706 12.2999C83.9706 14.4072 83.0149 15.8089 81.1133 16.5049C82.1373 16.7562 82.9466 17.2492 83.522 17.9936C84.0973 18.7379 84.3899 19.6079 84.3899 20.6326C84.3899 22.4789 83.756 23.8516 82.4786 24.7506C81.2011 25.6399 79.2216 26.1039 76.5301 26.1232H67.7927V26.1136ZM73.3804 14.9099H76.023C76.8714 14.9002 77.476 14.7456 77.8368 14.4556C78.1976 14.1656 78.3732 13.7306 78.3732 13.1506C78.3732 12.4642 78.1879 11.9712 77.8173 11.6909C77.4468 11.4106 76.8617 11.2656 76.0718 11.2656H73.3804V14.9099ZM73.3804 18.3706V21.8506H76.3253C77.086 21.8506 77.6906 21.6959 78.1294 21.3962C78.5682 21.0966 78.7925 20.6809 78.7925 20.1686C78.7925 19.0182 78.1099 18.4189 76.7544 18.3706H73.3804Z"
              fill="#EB743B"
            />
            <path
              d="M96.8133 14.3879L95.1263 14.2719C93.5173 14.2719 92.4836 14.7745 92.0253 15.7799V26.1135H86.896V9.78654H91.7035L91.8693 11.8842C92.7274 10.2892 93.9366 9.48688 95.4774 9.48688C96.0235 9.48688 96.5013 9.54488 96.9108 9.67054L96.8231 14.3879H96.8133Z"
              fill="#EB743B"
            />
            <path
              d="M107.482 26.1136C107.296 25.7849 107.14 25.2919 106.994 24.6539C106.048 25.8332 104.732 26.4229 103.035 26.4229C101.484 26.4229 100.168 25.9589 99.0758 25.0309C97.9934 24.1029 97.4473 22.9332 97.4473 21.5219C97.4473 19.7529 98.1104 18.4092 99.4268 17.5102C100.743 16.6016 102.664 16.1569 105.18 16.1569H106.76V15.2966C106.76 13.7886 106.107 13.0346 104.8 13.0346C103.581 13.0346 102.976 13.6339 102.976 14.8229H97.8471C97.8471 13.2472 98.5199 11.9616 99.8754 10.9852C101.231 9.99923 102.957 9.50623 105.053 9.50623C107.15 9.50623 108.818 10.0186 110.027 11.0336C111.246 12.0486 111.87 13.4406 111.899 15.2096V22.4402C111.919 23.9386 112.153 25.0889 112.601 25.8816V26.1426H107.472L107.482 26.1136ZM104.273 22.7979C104.917 22.7979 105.444 22.6626 105.863 22.3919C106.282 22.1212 106.584 21.8119 106.77 21.4736V18.8636H105.278C103.493 18.8636 102.596 19.6562 102.596 21.2512C102.596 21.7152 102.752 22.0922 103.064 22.3726C103.376 22.6626 103.776 22.7979 104.264 22.7979H104.273Z"
              fill="#EB743B"
            />
            <path
              d="M114.707 5.56223C114.707 4.83723 114.971 4.2379 115.497 3.7739C116.024 3.3099 116.706 3.0779 117.555 3.0779C118.403 3.0779 119.086 3.3099 119.612 3.7739C120.139 4.2379 120.402 4.83723 120.402 5.56223C120.402 6.28723 120.139 6.88656 119.612 7.35056C119.086 7.81456 118.403 8.04656 117.555 8.04656C116.706 8.04656 116.024 7.81456 115.497 7.35056C114.971 6.88656 114.707 6.28723 114.707 5.56223ZM120.159 26.1136H115.01V9.78656H120.159V26.1136Z"
              fill="#EB743B"
            />
            <path
              d="M128.028 9.78654L128.194 11.7005C129.335 10.2215 130.895 9.48688 132.894 9.48688C134.61 9.48688 135.888 9.99921 136.736 11.0142C137.585 12.0292 138.023 13.5565 138.053 15.6059V26.1232H132.904V15.8185C132.904 14.9969 132.738 14.3879 132.397 14.0012C132.065 13.6145 131.451 13.4212 130.573 13.4212C129.569 13.4212 128.828 13.8175 128.34 14.6005V26.1232H123.211V9.78654H128.018H128.028Z"
              fill="#EB743B"
            />
            <path
              d="M146.946 22.1889H154.445V26.1136H140.461V23.2812L147.765 13.7209H140.783V9.79623H154.279V12.5416L146.946 22.1986V22.1889Z"
              fill="#EB743B"
            />
          </g>
          <defs>
            <clipPath id="clip0_3_261">
              <rect
                width="157"
                height="29"
                fill="white"
                transform="translate(0 0.980225)"
              />
            </clipPath>
          </defs>
        </svg>
      </p>
    </div>
  );
}
