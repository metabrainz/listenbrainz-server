import * as React from "react";
import { act, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "../../test-utils/rtl-test-utils";
import { ReactQueryWrapper } from "../../test-react-query";
import LBRadio from "../../../src/explore/lb-radio/LBRadio";
import APIService from "../../../src/utils/APIService";
import {
  ambientQueueAtom,
  store,
} from "../../../src/common/brainzplayer/BrainzPlayerAtoms";

// Capture the sortable list props so the tests can simulate a drag and drop
let sortableProps: { setList: (list: any[]) => void } | undefined;
jest.mock("react-sortablejs", () => ({
  ReactSortable: (props: any) => {
    sortableProps = props;
    const { children } = props;
    return <div>{children}</div>;
  },
}));

jest.mock("react-router", () => ({
  ...jest.requireActual("react-router"),
  useLoaderData: () => ({ mode: "easy", prompt: "artist:(Moondog)" }),
}));

const makeTrack = (id: string, title: string): JSPFTrack => ({
  id,
  identifier: [`https://musicbrainz.org/recording/${id}`],
  title,
  creator: "Moondog",
});

const renderLBRadio = (tracks: JSPFTrack[]) => {
  const testAPIService = new APIService("");
  testAPIService.getLBRadioPlaylist = jest.fn().mockResolvedValue({
    payload: {
      jspf: {
        playlist: {
          title: "LB Radio for artist Moondog",
          annotation: "",
          creator: "listenbrainz",
          identifier: "",
          date: "",
          track: tracks,
        },
      },
      feedback: [],
    },
  });
  testAPIService.getRecordingMetadata = jest.fn().mockResolvedValue({});
  return renderWithProviders(
    <ReactQueryWrapper>
      <LBRadio />
    </ReactQueryWrapper>,
    { APIService: testAPIService }
  );
};

const getRemoveButtons = () =>
  screen.findAllByRole("menuitem", { name: "Remove from playlist" });

describe("LB Radio page", () => {
  beforeEach(() => {
    store.set(ambientQueueAtom, []);
  });

  it("removes a track from the page queue when it is removed from the radio", async () => {
    renderLBRadio([
      makeTrack("aaaaaaaa-0000-0000-0000-000000000001", "Bird's Lament"),
      makeTrack("aaaaaaaa-0000-0000-0000-000000000002", "Stamping Ground"),
    ]);
    const removeButtons = await getRemoveButtons();
    expect(removeButtons).toHaveLength(2);
    expect(store.get(ambientQueueAtom)).toHaveLength(2);

    await userEvent.click(removeButtons[0]);

    await waitFor(() => {
      expect(store.get(ambientQueueAtom)).toHaveLength(1);
    });
    expect(store.get(ambientQueueAtom)[0].track_metadata.track_name).toEqual(
      "Stamping Ground"
    );
  });

  it("empties the page queue when the last track is removed", async () => {
    renderLBRadio([
      makeTrack("aaaaaaaa-0000-0000-0000-000000000001", "Bird's Lament"),
    ]);
    const removeButtons = await getRemoveButtons();
    expect(removeButtons).toHaveLength(1);
    expect(store.get(ambientQueueAtom)).toHaveLength(1);

    await userEvent.click(removeButtons[0]);

    await waitFor(() => {
      expect(store.get(ambientQueueAtom)).toHaveLength(0);
    });
    expect(screen.getByText("No playlist was generated.")).toBeInTheDocument();
  });

  it("reorders the page queue when tracks are dragged to a new position", async () => {
    renderLBRadio([
      makeTrack("aaaaaaaa-0000-0000-0000-000000000001", "Bird's Lament"),
      makeTrack("aaaaaaaa-0000-0000-0000-000000000002", "Stamping Ground"),
    ]);
    await getRemoveButtons();
    expect(sortableProps).toBeDefined();
    const getQueueTitles = () =>
      store
        .get(ambientQueueAtom)
        .map((listen) => listen.track_metadata.track_name);
    expect(getQueueTitles()).toEqual(["Bird's Lament", "Stamping Ground"]);

    const [first, second] = (sortableProps as any).list;
    await act(async () => {
      sortableProps?.setList([second, first]);
    });

    await waitFor(() => {
      expect(getQueueTitles()).toEqual(["Stamping Ground", "Bird's Lament"]);
    });
  });
});
