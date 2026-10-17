import * as React from "react";
import { render, waitFor } from "@testing-library/react";
import { toast } from "react-toastify";

const mockLocalForageStore = new Map<string, unknown>();
const mockKeys = jest.fn(() =>
  Promise.resolve(Array.from(mockLocalForageStore.keys()))
);
const mockSetItem = jest.fn((key: string, value: unknown) => {
  mockLocalForageStore.set(key, value);
  return Promise.resolve(value);
});

jest.mock("localforage", () => ({
  __esModule: true,
  default: {
    INDEXEDDB: "INDEXEDDB",
    LOCALSTORAGE: "LOCALSTORAGE",
    createInstance: jest.fn(() => ({
      keys: mockKeys,
      setItem: mockSetItem,
    })),
  },
}));

jest.mock("react-toastify", () => ({
  toast: jest.fn(),
  ToastContainer: () => null,
}));

jest.mock("react-router", () => ({
  Outlet: () => null,
  ScrollRestoration: () => null,
}));

jest.mock("../../src/components/Footer", () => () => null);
jest.mock("../../src/components/Navbar", () => () => null);
jest.mock("../../src/utils/ProtectedRoutes", () => () => null);

let Layout: typeof import("../../src/layout").default;

describe("Layout initial alerts", () => {
  const initialAlerts = [
    {
      id: "test-alert",
      level: "info" as const,
      message: "Test alert",
    },
  ];

  beforeEach(() => {
    mockLocalForageStore.clear();
    jest.clearAllMocks();
  });

  beforeAll(async () => {
    const layoutModule = await import("../../src/layout");
    Layout = layoutModule.default;
  });

  it("stores dismissed initial alerts and skips them on later renders", async () => {
    const { unmount } = render(
      <Layout initialAlerts={initialAlerts} withBrainzPlayer={false} />
    );

    await waitFor(() => expect(toast).toHaveBeenCalledTimes(1));
    const mockedToast = toast as unknown as jest.Mock;
    const toastOptions = mockedToast.mock.calls[0][1];
    expect(toastOptions.toastId).toBe("test-alert");

    toastOptions.onClose();

    await waitFor(() =>
      expect(mockLocalForageStore.get("test-alert")).toBe(true)
    );

    unmount();
    jest.clearAllMocks();
    render(<Layout initialAlerts={initialAlerts} withBrainzPlayer={false} />);

    await waitFor(() => expect(mockKeys).toHaveBeenCalledTimes(1));
    expect(toast).not.toHaveBeenCalled();
  });
});
