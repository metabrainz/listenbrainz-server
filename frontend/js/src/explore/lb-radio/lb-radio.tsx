/* eslint-disable jsx-a11y/anchor-is-valid */

import { createRoot } from "react-dom/client";
import * as React from "react";
import NiceModal from "@ebay/nice-modal-react";
import ErrorBoundary from "../../utils/ErrorBoundary";
import GlobalAppContext, {
  GlobalAppContextT,
} from "../../utils/GlobalAppContext";
import { getPageProps } from "../../utils/utils";

//import BrainzPlayer from "../../brainzplayer/BrainzPlayer";
//import ListenCard from "../../listens/ListenCard";
//import Card from "../../components/Card";

function UserFeedback(props) {
    const { feedback } = props;

    return (
      <div className="feedback">
        <div className="feedback-header">
          Prompt feedback:
        </div>
        <ul>
          <li>Feedback #1</li>
          <li>Feedback #2</li>
          <li>Feedback #3</li>
        </ul>
      </div>  
    );
}

function Playlist(props) {
    const { playlist } = props;
    return (
      <div>
         <div>Playlist item #1</div>
         <div>Playlist item #2</div>
         <div>Playlist item #3</div>
      </div>
    );
}

function Prompt(props) {
    const { onGenerate } = props;
   
    const callbackFunction = React.useCallback((event: React.FormEvent) => {
      console.log(event); 
      event.preventDefault(); 
      
      const form = event.target;
      const formData = new FormData(form);
      const prompt = formData.get("prompt");
      
      onGenerate(prompt);
    }, [ onGenerate ]);
 
    return (
        <div className="prompt">
          <div>
            <h3>ListenBrainz Radio playlist generator</h3> 
          </div>
          <form className="row" onSubmit={callbackFunction}>
            <div className="col-sm-10">
              <input type="text" className="prompt-text form-control form-control-lg" id="prompt" placeholder="Enter prompt..."/>
            </div>
            <div className="col-sm-2">
              <button type="submit" className="btn btn-lg btn-primary">Generate</button>
            </div>
          </form>
          <div className="">
            <a href="https://troi.readthedocs.io/en/lb-radio/lb_radio.html">documentation</a>
          </div>
        </div>
    );
}

function LBRadio() {
  const [jspfPlaylist, setJspfPlaylist] = React.useState({});
  const [feedback, setFeedback] = React.useState([]);
  
  const generatePlaylistCallback = React.useCallback(
        async (prompt) => { 
          console.log("hi mom! ",prompt)
          try {
            const request = await fetch(`https://api-test.listenbrainz.org/1/explore/lb-radio?prompt=${prompt}&mode=easy`);
            if (request.ok) {
               const payload = await request.json();
               console.log(payload.feedback)
               setJspfPlaylist(payload.jspf);
               setFeedback(payload.feedback);
            }
          }
          catch (error) {
             console.log(error);
          }
        }
    , [setJspfPlaylist, setFeedback])
  
  return (
      <div className="row">
        <div className="col-sm-12">
          <Prompt onGenerate={generatePlaylistCallback} />
          <UserFeedback feedback={feedback} />
          <Playlist playlist={jspfPlaylist} />
        </div>
      </div>);
}

document.addEventListener("DOMContentLoaded", () => {
  const { domContainer, reactProps, globalAppContext } = getPageProps();

//  const { user } = reactProps;

  const renderRoot = createRoot(domContainer!);
  renderRoot.render(
    <ErrorBoundary>
      <GlobalAppContext.Provider value={globalAppContext}>
        <NiceModal.Provider>
          <LBRadio />
        </NiceModal.Provider>
      </GlobalAppContext.Provider>
    </ErrorBoundary>
  );
});
