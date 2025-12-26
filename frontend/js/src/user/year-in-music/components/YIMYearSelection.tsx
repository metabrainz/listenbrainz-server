import React from "react";
import { debounce, noop, throttle } from "lodash";
import { Link, useNavigate } from "react-router";
import GlobalAppContext from "../../../utils/GlobalAppContext";
import { generateAlbumArtThumbnailLink } from "../../../utils/utils";
import type { YearInMusicLayoutData } from "../layout";

type YIMYearSelectionProps = {
  year: number;
  encodedUsername: string;
  data: YearInMusicLayoutData[];
};

export default function YIMYearSelection({
  year,
  encodedUsername,
  data,
}: YIMYearSelectionProps) {
  const navigate = useNavigate();
  const { APIService } = React.useContext(GlobalAppContext);
  const selectedRef = React.useRef<HTMLAnchorElement>(null);
  const yearSelectionRef = React.useRef<HTMLDivElement>(null);
  const isInitialEvent = React.useRef<boolean>(true);

  const availableYears = data.map((item) => item.year).sort((a, b) => a - b);
  const transformedData = data.reduce(
    (acc: Record<number, YearInMusicLayoutData>, item) => {
      acc[item.year] = item;
      return acc;
    },
    {} as Record<number, YearInMusicLayoutData>
  );

  const handleYearClick = React.useCallback(
    (e: React.MouseEvent<HTMLAnchorElement>) => {
      e.preventDefault();
      const selectThisYear = e.currentTarget?.dataset?.year;
      if (selectThisYear) {
        navigate(`./${selectThisYear}/`, {
          preventScrollReset: true,
          replace: true,
        });
        e.currentTarget.scrollIntoView({
          behavior: "smooth",
          inline: "center",
          block: "start",
          // @ts-expect-error container not recognized in TS
          container: "nearest",
        });
      }
    },
    [navigate]
  );
  React.useEffect(() => {
    if (selectedRef.current) {
      selectedRef.current.scrollIntoView({
        behavior: "instant",
        inline: "center",
        block: "start",
        // @ts-expect-error container not recognized in TS
        container: "nearest",
      });
    }
  }, []);
  React.useEffect(() => {
    if (!yearSelectionRef.current) return noop;
    const innerRef = yearSelectionRef.current;
    const onScrollSnapChange = (e: Event) => {
      // @ts-expect-error Cannot find a SnapEvent type in TS yet, so snapTargetInline is not recognized
      const selectThisYear = e.snapTargetInline?.dataset?.year;
      if (isInitialEvent.current === true) {
        // Ignore the first event fired on initial scrollIntoView (page load)
        isInitialEvent.current = false;
      } else if (selectThisYear) {
        navigate(`./${selectThisYear}/`, {
          preventScrollReset: true,
          replace: true,
        });
      }
    };
    const onScrollSnapChanging = (e: Event) => {
      // @ts-expect-error Cannot find a SnapEvent type in TS yet, so snapTargetInline is not recognized
      const target = e.snapTargetInline;
      if (target) {
        const elementsWithSelectedClass = target.parentElement.querySelectorAll(
          ".selected"
        );
        elementsWithSelectedClass.forEach((selected: HTMLElement) => {
          selected.classList.remove("selected");
        });
        target.classList.add("selected");
      }
    };
    const debouncedonScrollSnapChange = debounce(onScrollSnapChange, 800, {
      leading: false,
      trailing: true,
    });
    const debouncedonScrollSnapChanging = throttle(onScrollSnapChanging, 250);
    innerRef.addEventListener("scrollsnapchange", debouncedonScrollSnapChange);
    innerRef.addEventListener(
      "scrollsnapchanging",
      debouncedonScrollSnapChanging
    );
    return () => {
      innerRef.removeEventListener(
        "scrollsnapchange",
        debouncedonScrollSnapChange
      );
      innerRef.removeEventListener(
        "scrollsnapchanging",
        debouncedonScrollSnapChanging
      );
    };
  }, [yearSelectionRef, navigate]);

  return (
    <div className="year-selection mb-5" ref={yearSelectionRef}>
      <div className="leading-line" />
      {availableYears.map((availableYear, idx) => {
        const yearData = transformedData[availableYear];
        const { cover_art } = yearData || {};
        const { caa_id, caa_release_mbid } = cover_art || {};
        const isSelectedYear = availableYear === year;
        let coverURL = `${APIService.APIBaseURI}/art/grid-stats/${encodedUsername}/this_year/1/0/250?caption=false`;
        if (caa_id && caa_release_mbid) {
          coverURL = generateAlbumArtThumbnailLink(caa_id, caa_release_mbid);
        }
        return (
          <Link
            key={availableYear}
            to={`./${availableYear}/`}
            ref={isSelectedYear ? selectedRef : null}
            className={`year-item ${isSelectedYear ? "selected" : ""}`}
            onClick={handleYearClick}
            data-year={availableYear}
          >
            <div className="year-image">
              <img src={coverURL} alt={`Cover for year ${availableYear}`} />
            </div>
            <div className="year-separator">
              <div className="year-connector" />
              <div className="year-marker" />
              <div className="year-connector" />
            </div>
            <div className="year-number">{availableYear}</div>
          </Link>
        );
      })}
      <div className="trailing-line" />
    </div>
  );
}
