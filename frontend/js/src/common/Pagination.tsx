/* eslint-disable jsx-a11y/anchor-is-valid */
import * as React from "react";

type PaginationProps = {
  currentPageNo: number;
  totalPageCount: number;
  handleClickPrevious: () => void;
  handleClickNext: () => void;
};

export default function Pagination(props: PaginationProps) {
  const {
    currentPageNo,
    totalPageCount,
    handleClickPrevious,
    handleClickNext,
  } = props;
  return (
    <nav role="navigation" aria-label="Pagination" style={{ maxWidth: "none" }}>
      <ul className="pagination" style={{ display: "flex" }}>
        <li
          className={`page-item ${
            currentPageNo && currentPageNo <= 1 ? "hidden" : ""
          }`}
        >
          <a
            role="button"
            onClick={handleClickPrevious}
            onKeyDown={(e) => {
              if (e.key === "Enter") handleClickPrevious();
            }}
            tabIndex={0}
            aria-disabled={Boolean(currentPageNo && currentPageNo <= 1)}
            aria-label={`Go to page ${Math.max(currentPageNo - 1, 0)}`}
            className="page-link"
          >
            &larr; Previous
          </a>
        </li>
        <li
          className={`page-item ${
            currentPageNo && currentPageNo >= totalPageCount ? "hidden" : ""
          }`}
          style={{ marginLeft: "auto" }}
        >
          <a
            role="button"
            onClick={handleClickNext}
            onKeyDown={(e) => {
              if (e.key === "Enter") handleClickNext();
            }}
            tabIndex={0}
            aria-disabled={Boolean(
              currentPageNo && currentPageNo >= totalPageCount
            )}
            aria-label={`Go to page ${Math.min(
              currentPageNo + 1,
              totalPageCount
            )}`}
            className="page-link"
          >
            Next &rarr;
          </a>
        </li>
      </ul>
    </nav>
  );
}
