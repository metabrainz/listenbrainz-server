import { isString } from "lodash";
import React, { useState } from "react";

export enum Modes {
  "easy",
  "medium",
  "hard",
}

type PromptProps = {
  onGenerate: (prompt: string, mode: Modes) => void;
  errorMessage: string;
  initMode: Modes;
  initPrompt: string;
};

function Prompt(props: PromptProps) {
  const { onGenerate, errorMessage, initMode, initPrompt } = props;
  const [prompt, setPrompt] = useState<string>(initPrompt);
  const [mode, setMode] = useState<Modes>(initMode || Modes.easy);
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
      // casting as Mode type here should be fine
      // since we generated the options programatically from the enum
      setMode((text as unknown) as Modes);
    },
    []
  );

  React.useEffect(() => {
    if (initPrompt.length > 0) {
      setHideExamples(true);
      onGenerate(initPrompt, initMode);
    }
  }, [initMode, initPrompt, onGenerate]);

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
            {Object.values(Modes)
              .filter(isString)
              .map((modeName) => {
                return <option value={modeName}>{modeName}</option>;
              })}
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
