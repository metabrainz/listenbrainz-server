import * as React from "react";
import { get as _get, isString } from "lodash";
import hljs from "highlight.js/lib/core";
import { sanitize } from "dompurify";

const json = require("highlight.js/lib/languages/json");

hljs.registerLanguage("json", json);

export interface SimpleModalI {
  updateModal: (
    header: string | JSX.Element,
    body: string | JSX.Element,
    footer: string | JSX.Element,
    highlightCode: boolean
  ) => void;
  onClose?: () => void;
}

export type SimpleModalProps = {};

export interface SimpleModalState {
  header?: string | JSX.Element;
  body: string | JSX.Element;
  footer?: string | JSX.Element;
  highlightCode?: boolean;
}

export type WithSimpleModalInjectedProps = {
  updateModal: (
    header: string | JSX.Element,
    body: string | JSX.Element,
    footer: string | JSX.Element,
    highlightCode?: boolean
  ) => void;
};

export default class SimpleModal
  extends React.Component<SimpleModalProps, SimpleModalState>
  implements SimpleModalI {
  constructor(props: SimpleModalProps) {
    super(props);
    this.state = {
      body: "",
    };
  }

  public updateModal(
    body: string | JSX.Element,
    header?: string | JSX.Element,
    footer?: string | JSX.Element,
    highlightCode: boolean = false
  ) {
    this.setState({ header, body, footer, highlightCode });
    // Currently taken care of by Bootstrap3 and jQuery
    // this.setState({ isOpen: true });
  }

  // Currently taken care of by Bootstrap3 and jQuery
  // closeModal(){
  // 	this.setState({isOpen:false});
  // }

  render() {
    const { header, body, footer, highlightCode } = this.state;
    let manipulatedBody = body;
    if (highlightCode && isString(body)) {
      const highlightedBody = hljs.highlightAuto(body).value;
      manipulatedBody = (
        <pre>
          <code
            className="hljs"
            // eslint-disable-next-line react/no-danger
            dangerouslySetInnerHTML={{
              __html: sanitize(highlightedBody),
            }}
          />
        </pre>
      );
    }
    return (
      <div
        className="modal fade"
        id="SimpleModal"
        tabIndex={-1}
        role="dialog"
        aria-labelledby="SimpleModalLabel"
        data-backdrop="static"
      >
        <div className="modal-dialog" role="document">
          <form className="modal-content">
            <div className="modal-header">
              <button
                type="button"
                className="close"
                data-dismiss="modal"
                aria-label="Close"
              >
                <span aria-hidden="true">&times;</span>
              </button>
              {header && (
                <h4 className="modal-title" id="SimpleModalLabel">
                  {header}
                </h4>
              )}
            </div>
            <div className="modal-body">{manipulatedBody}</div>
            {footer && <div className="modal-footer">{footer}</div>}
          </form>
        </div>
      </div>
    );
  }
}
