import * as React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import SubsonicServiceCard, {
  SubsonicService,
} from "../../../src/settings/music-services/details/components/SubsonicServiceCard";

jest.mock("react-toastify", () => ({
  toast: {
    success: jest.fn(),
    error: jest.fn(),
  },
}));

function jsonResponse(body = {}, ok = true) {
  return Promise.resolve({
    ok,
    status: ok ? 200 : 400,
    statusText: ok ? "OK" : "Bad Request",
    headers: {
      get: () => "application/json",
    },
    json: () => Promise.resolve(body),
  } as unknown as Response);
}

type RenderProps = {
  service?: SubsonicService;
  displayName?: string;
  permission?: string;
  requiresHostUrl?: boolean;
  fixedHostUrl?: string;
  auth?: {
    instance_url?: string;
    username?: string;
  };
  onConnected?: jest.Mock;
};

function renderCard(props: RenderProps = {}) {
  const service = props.service || "bandcamp";
  const displayName = props.displayName || "Bandcamp";
  const onConnected = props.onConnected || jest.fn();
  render(
    <SubsonicServiceCard
      service={service}
      displayName={displayName}
      permission={props.permission || "disable"}
      auth={props.auth}
      authToken="AUTH_TOKEN"
      fixedHostUrl={props.fixedHostUrl}
      requiresHostUrl={props.requiresHostUrl}
      hostPlaceholder="https://navidrome.example.com/"
      description={<>Connect to {displayName}.</>}
      warning={
        <>
          <strong>Important:</strong> Check your credentials.
        </>
      }
      connectDetails={`Connect to ${displayName}.`}
      disableDetails={`Disable ${displayName}.`}
      handlePermissionChange={jest.fn()}
      onConnected={onConnected}
    />
  );
  return { onConnected };
}

describe("SubsonicServiceCard", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    const fetchMock = jest.fn(() => jsonResponse()) as jest.Mock;
    global.fetch = fetchMock;
    window.fetch = fetchMock;
  });

  it("connects Bandcamp without sending a host URL", async () => {
    const user = userEvent.setup();
    const { onConnected } = renderCard({
      service: "bandcamp",
      displayName: "Bandcamp",
      fixedHostUrl: "https://bandcamp.com/api/subsonic",
    });

    expect(
      screen.queryByLabelText("Your Bandcamp server URL:")
    ).not.toBeInTheDocument();

    await user.type(screen.getByLabelText("Username:"), "bandcamp-user");
    await user.type(screen.getByLabelText("Password:"), "bandcamp-password");
    expect(screen.getByLabelText("Password:")).toHaveValue(
      "bandcamp-password"
    );
    await user.click(
      screen.getByRole("radio", { name: /Connect to Bandcamp/i })
    );

    await waitFor(() => {
      expect(window.fetch).toHaveBeenCalledWith(
        "/settings/music-services/bandcamp/connect/",
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({
            username: "bandcamp-user",
            password: "bandcamp-password",
          }),
        })
      );
    });
    expect(onConnected).toHaveBeenCalledWith("bandcamp", {
      instance_url: "https://bandcamp.com/api/subsonic",
      username: "bandcamp-user",
    });
  });

  it("connects Navidrome with a normalized host URL", async () => {
    const user = userEvent.setup();
    const { onConnected } = renderCard({
      service: "navidrome",
      displayName: "Navidrome",
      requiresHostUrl: true,
    });

    await user.type(
      screen.getByLabelText("Your Navidrome server URL:"),
      "https://navidrome.example.com/"
    );
    await user.type(screen.getByLabelText("Username:"), "navidrome-user");
    await user.type(screen.getByLabelText("Password:"), "navidrome-password");
    expect(screen.getByLabelText("Password:")).toHaveValue(
      "navidrome-password"
    );
    await user.click(
      screen.getByRole("radio", { name: /Connect to Navidrome/i })
    );

    await waitFor(() => {
      expect(window.fetch).toHaveBeenCalledWith(
        "/settings/music-services/navidrome/connect/",
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({
            username: "navidrome-user",
            password: "navidrome-password",
            host_url: "https://navidrome.example.com",
          }),
        })
      );
    });
    expect(onConnected).toHaveBeenCalledWith("navidrome", {
      instance_url: "https://navidrome.example.com",
      username: "navidrome-user",
    });
  });

  it("reveals password input when editing an existing connection", async () => {
    const user = userEvent.setup();
    renderCard({
      service: "navidrome",
      displayName: "Navidrome",
      permission: "listen",
      requiresHostUrl: true,
      auth: {
        instance_url: "https://navidrome.example.com",
        username: "existing-user",
      },
    });

    expect(screen.queryByLabelText("Password:")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Edit" }));

    expect(screen.getByLabelText("Password:")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Save" })).toBeInTheDocument();
  });
});
