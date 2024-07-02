/* eslint-disable import/prefer-default-export, import/no-extraneous-dependencies */
import * as React from "react";
import { RenderOptions, render } from "@testing-library/react";
import { ToastContainer } from "react-toastify";
import { isString } from "lodash";
import { BrowserRouter } from "react-router-dom";
import APIService from "../../src/utils/APIService";
import GlobalAppContext, {
  GlobalAppContextT,
} from "../../src/utils/GlobalAppContext";
import RecordingFeedbackManager from "../../src/utils/RecordingFeedbackManager";

/*
This shouldn't be required once we move all the tests away
from Enzyme to RTL, and the file at frontend/js/tests/__mocks__/react-toastify.js
will need to be be deleted
*/
jest.unmock("react-toastify");
jest.requireActual("react-toastify");

const testAPIService = new APIService("");
const defaultGlobalContext: GlobalAppContextT = {
  APIService: testAPIService,
  websocketsUrl: "",
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

export const renderWithProviders = (
  ui: React.ReactElement,
  globalContext?: Partial<GlobalAppContextT>,
  renderOptions?: RenderOptions,
  withRouter = true
) => {
  function WithProviders({ children }: { children: React.ReactElement }) {
    const globalProps = React.useMemo<GlobalAppContextT>(
      () => ({
        ...defaultGlobalContext,
        ...globalContext,
      }),
      []
    );

    const providers = (
      <GlobalAppContext.Provider value={globalProps}>
        <ToastContainer />
        {children}
      </GlobalAppContext.Provider>
    );
    if (!withRouter) return providers;
    return <BrowserRouter>{providers}</BrowserRouter>;
  }
  const { wrapper: MyWrapper, ...otherRenderOptions } = renderOptions ?? {};
  let wrapper = WithProviders;
  if (MyWrapper) {
    wrapper = ({ children }: { children: React.ReactElement }) =>
      WithProviders({ children: <MyWrapper>{children}</MyWrapper> });
  }
  return render(ui, { wrapper, ...otherRenderOptions });
};

/**
 * Getting the deepest element that contain string / match regex even when it split between multiple elements
 * Based on  https://github.com/testing-library/dom-testing-library/issues/410#issuecomment-1060917305
 *
 * @example
 * For:
 * <div>
 *   <span>Hello</span><span> World</span>
 * </div>
 *
 * screen.getByText('Hello World') // ❌ Fail
 * screen.getByText(textContentMatcher('Hello World')) // ✅ pass
 */
export function textContentMatcher(textMatch: string | RegExp) {
  const hasText =
    typeof textMatch === "string"
      ? (node: Element) => node.textContent === textMatch
      : (node: Element) =>
          isString(node?.textContent) && textMatch.test(node.textContent);

  const matcher = (_content: string, node: Element | null) => {
    if (node === null || !hasText(node)) {
      return false;
    }

    const childrenDontHaveText = Array.from(node?.children || []).every(
      (child) => !hasText(child)
    );

    return childrenDontHaveText;
  };
  matcher.toString = () => `textContentMatcher(${textMatch})`;

  return matcher;
}
