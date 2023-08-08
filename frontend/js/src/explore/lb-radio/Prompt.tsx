/* eslint-disable jsx-a11y/anchor-is-valid */

import * as React from "react";
import { useState } from "react";

type PromptProps = {
  onGenerate: (prompt: string, mode: string) => void;
  errorMessage: string;
  initMode: string;
  initPrompt: string;
};

function Prompt(props: PromptProps) {
  const { onGenerate, errorMessage, initMode, initPrompt } = props;
  const [prompt, setPrompt] = useState<string>(initPrompt);
  const [mode, setMode] = useState<string>(initMode);
  const [hideExamples, setHideExamples] = React.useState(false);

  const generateCallbackFunction = React.useCallback(
    (event: React.FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      setHideExamples(true);
      onGenerate(prompt, mode);
    },
    [prompt, onGenerate, mode]
  );

  const onInputChangeCallback = React.useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      const text = event.target.value;
      setPrompt(text);
    },
    []
  );

  const onModeSelectChange = React.useCallback(
    (event: React.ChangeEvent<HTMLSelectElement>) => {
      const text = event.target.value;
      setMode(text);
    },
    []
  );

  React.useEffect(() => {
    if (prompt.length > 0) {
      setHideExamples(true);
      onGenerate(initPrompt, initMode);
    }
  }, [initMode, initPrompt, onGenerate, prompt.length]);

  return (
    <div className="prompt">
      <div>
        <h3>
          ListenBrainz Radio playlist generator
          <small>
            <a
              id="doc-link"
              href="https://troi.readthedocs.io/en/add-user-stats-entity/lb_radio.html"
            >
              How do I write a query?
            </a>
          </small>
        </h3>
      </div>
      <form onSubmit={generateCallbackFunction}>
        <div className="input-group input-group-flex" id="prompt-input">
          <input
            type="text"
            className="form-control form-control-lg"
            name="prompt"
            value={prompt}
            placeholder="Enter prompt..."
            onChange={onInputChangeCallback}
          />
          <select
            className="form-control"
            id="mode-dropdown"
            name="mode"
            value={mode}
            onChange={onModeSelectChange}
          >
            <option value="easy">easy</option>
            <option value="medium">medium</option>
            <option value="hard">hard</option>
          </select>
          <span className="input-group-btn">
            <button
              type="submit"
              className="btn btn-primary"
              disabled={prompt?.length <= 3}
            >
              Generate
            </button>
          </span>
        </div>
      </form>
      {hideExamples === false && (
        <div>
          <div id="examples">
            Examples:
            <a href="/explore/lb-radio?prompt=artist:(radiohead)&mode=easy">
              artist:(radiohead)
            </a>
            <a href="/explore/lb-radio?prompt=tag:(trip hop)&mode=easy">
              tag:(trip hop)
            </a>
            <a href="/explore/lb-radio?prompt=%23metal&mode=easy">#metal</a>
            <a href="/explore/lb-radio?prompt=stats:rob&mode=easy">stats:rob</a>
          </div>
          <div id="made-with-postgres">
            <img
              src="/static/img/explore/made-with-postgres.png"
              alt="Made with Postgres, not AI!"
            />
          </div>
        </div>
      )}
      {errorMessage.length > 0 && (
        <div id="error-message" className="alert alert-danger">
          {errorMessage}
        </div>
      )}
    </div>
  );
}

export default Prompt;
