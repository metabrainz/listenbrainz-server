import * as React from "react";
import { RenderOptions, render } from "@testing-library/react";
import { ToastContainer } from "react-toastify";
import APIService from "../../src/utils/APIService";
import GlobalAppContext, {
  GlobalAppContextT,
} from "../../src/utils/GlobalAppContext";
import RecordingFeedbackManager from "../../src/utils/RecordingFeedbackManager";

const testAPIService = new APIService("");
const defaultGlobalContext: GlobalAppContextT = {
  APIService: testAPIService,
  currentUser: {
    id: 1,
    name: "FNORD",
    auth_token: "never_gonna",
  },
  spotifyAuth: {},
  youtubeAuth: {},
  critiquebrainzAuth: {
    access_token: "giveyouup",
  },
  recordingFeedbackManager: new RecordingFeedbackManager(testAPIService, {
    name: "Fnord",
  }),
};

const customRender = (ui: React.ReactElement, globalContext?:Partial<GlobalAppContextT>, renderOptions?: RenderOptions) => {
  
  function WithProviders({ children }: { children: React.ReactElement }) {
    const globalProps = Object.assign({},defaultGlobalContext, globalContext);

    return (
      <>
        <GlobalAppContext.Provider value={globalProps}>
          {children}
        </GlobalAppContext.Provider>
        <ToastContainer
          position="bottom-right"
          hideProgressBar
          newestOnTop
          closeOnClick
          rtl={false}
          theme="light"
        />
      </>
    );
  }
  return render(ui, { wrapper: WithProviders, ...renderOptions });
}

// re-export everything
export * from '@testing-library/react'

// override render method
export {customRender as render}