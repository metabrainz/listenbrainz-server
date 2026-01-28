import NiceModal, { useModal, bootstrapDialog } from "@ebay/nice-modal-react";
import { Modal } from "react-bootstrap";
import * as React from "react";
import { useState } from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faCircleQuestion,
  faRssSquare,
} from "@fortawesome/free-solid-svg-icons";
import Tooltip from "react-tooltip";

type BaseOptionProps = {
  label: string;
  key: string;
  tooltip?: string;
};

type DropdownOption = BaseOptionProps & {
  type: "dropdown";
  values: { id: string; value: string; displayValue?: string }[];
  defaultIndex?: number;
};

type NumberOption = BaseOptionProps & {
  type: "number";
  min?: number;
  max?: number;
  defaultValue: number;
};

export type SyndicationFeedModalProps = {
  feedTitle: string;
  options: (DropdownOption | NumberOption)[];
  baseUrl: string;
};

type SelectedOptions = {
  [key: string]: string;
};

export default NiceModal.create((props: SyndicationFeedModalProps) => {
  const modal = useModal();

  const { feedTitle, options, baseUrl } = props;

  const initialSelectedOptions: SelectedOptions = options.reduce(
    (acc: SelectedOptions, option) => {
      if (option.type === "number") {
        acc[option.key] = option.defaultValue.toString();
      } else {
        const defaultIndex = option.defaultIndex ?? 0;
        acc[option.key] = option.values[defaultIndex].value;
      }
      return acc;
    },
    {}
  );

  const [selectedOptions, setSelectedOptions] = React.useState<SelectedOptions>(
    initialSelectedOptions
  );

  const [copyButtonText, setCopyButtonText] = useState("Copy");

  const handleOptionChange = (key: string, value: string) => {
    setSelectedOptions((prevSelectedOptions) => ({
      ...prevSelectedOptions,
      [key]: value,
    }));
  };

  const buildLink = () => {
    const queryParams = new URLSearchParams(selectedOptions).toString();
    return queryParams ? `${baseUrl}?${queryParams}` : baseUrl;
  };

  const handleCopyClick = () => {
    navigator.clipboard.writeText(buildLink()).then(() => {
      setCopyButtonText("Copied");

      setTimeout(() => {
        setCopyButtonText("Copy");
      }, 2000);
    });
  };

  return (
    <Modal
      size="lg"
      {...bootstrapDialog(modal)}
      title="Syndication feed"
      aria-labelledby="SyndicationFeedModalLabel"
      id="SyndicationFeedModal"
    >
      <Modal.Header closeButton>
        <Modal.Title id="SyndicationFeedModalLabel">
          <FontAwesomeIcon icon={faRssSquare} />
          &nbsp; Syndication feed: {feedTitle}
        </Modal.Title>
      </Modal.Header>
      <Modal.Body>
        {options.map((option) => (
          <div className="mb-4" key={option.key}>
            <label className="form-label" htmlFor={option.key}>
              {option.label}
              {option.tooltip && (
                <>
                  &nbsp;
                  <FontAwesomeIcon
                    icon={faCircleQuestion}
                    data-tip={option.tooltip}
                  />
                  <Tooltip place="right" type="dark" effect="solid" />
                </>
              )}
            </label>
            {option.type === "dropdown" && (
              <select
                className="form-select"
                id={option.key}
                onChange={(e) => handleOptionChange(option.key, e.target.value)}
                defaultValue={selectedOptions[option.key]}
              >
                {option.values.map((value) => (
                  <option key={value.id} value={value.value}>
                    {value.displayValue || value.value}
                  </option>
                ))}
              </select>
            )}
            {option.type === "number" && (
              <input
                type="number"
                className="form-control"
                id={option.key}
                value={selectedOptions[option.key]}
                min={option.min}
                max={option.max}
                onChange={(e) => handleOptionChange(option.key, e.target.value)}
              />
            )}
          </div>
        ))}
        <label className="form-label" htmlFor="feedLink">
          Subscription URL
        </label>
        <div className="btn-group d-flex">
          <input
            type="text"
            className="form-control"
            id="feedLink"
            value={buildLink()}
            readOnly
          />
          <button
            type="button"
            className="btn btn-info"
            onClick={handleCopyClick}
            style={{ minWidth: "100px" }}
          >
            {copyButtonText}
          </button>
        </div>
      </Modal.Body>
      <Modal.Footer>
        <button
          type="button"
          className="btn btn-secondary"
          onClick={modal.hide}
        >
          Close
        </button>
      </Modal.Footer>
    </Modal>
  );
});
