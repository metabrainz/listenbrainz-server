import * as React from "react";
import { Dropdown } from "react-bootstrap";
import DOMPurify from "dompurify";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faBell } from "@fortawesome/free-solid-svg-icons";
import GlobalAppContext from "../utils/GlobalAppContext";
import { preciseTimestamp } from "../utils/utils";
import createSynapseApi, {
  InboxNotification,
  Payloads,
  SynapseApi,
} from "./synapseApi";

const LIST_LIMIT = 20;

type Rendered = { text: React.ReactNode; href?: string };

const renderers: {
  [K in keyof Payloads]: (payload: Payloads[K]) => Rendered;
} = {
  follow: ({ actor }) => ({
    text: (
      <>
        <strong>{actor.username}</strong> started following you
      </>
    ),
    href: actor.url,
  }),
  notification: ({ actor, message }) => ({
    text: (
      <>
        <strong>{actor.username}</strong>:{" "}
        <span
          // Notifications come from approved senders and may contain links.
          // eslint-disable-next-line react/no-danger
          dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(message) }}
        />
      </>
    ),
  }),
  cb_review: ({ actor, entity }) => ({
    text: (
      <>
        <strong>{actor.username}</strong> reviewed{" "}
        <strong>{entity.name}</strong>
      </>
    ),
    href: entity.url,
  }),
  recording_pin: ({ actor, recording }) => ({
    text: (
      <>
        <strong>{actor.username}</strong> pinned{" "}
        <strong>{recording.track_name}</strong> by {recording.artist_name}
      </>
    ),
    href: recording.url ?? actor.url,
  }),
  recording_recommendation: ({ actor, recording }) => ({
    text: (
      <>
        <strong>{actor.username}</strong> recommended{" "}
        <strong>{recording.track_name}</strong> by {recording.artist_name}
      </>
    ),
    href: recording.url ?? actor.url,
  }),
  personal_recording_recommendation: ({ actor, recording, message }) => ({
    text: (
      <>
        <strong>{actor.username}</strong> recommended{" "}
        <strong>{recording.track_name}</strong> to you
        {message && `: ${message}`}
      </>
    ),
    href: recording.url ?? actor.url,
  }),
  thanks: ({ actor, recording }) => ({
    text: (
      <>
        <strong>{actor.username}</strong> thanked you for{" "}
        <strong>{recording.track_name}</strong>
      </>
    ),
    href: recording.url ?? actor.url,
  }),
};

// Synapse validated the payload against its event schema, so the cast holds.
// Unknown event types return null, so a new type doesn't break an older page.
function render(n: InboxNotification): Rendered | null {
  const renderer = renderers[n.event_type as keyof Payloads];
  return renderer ? (renderer as (p: unknown) => Rendered)(n.payload) : null;
}

export default function NotificationBell() {
  const { synapseUrl, musicbrainzAuth } = React.useContext(GlobalAppContext);
  const api = React.useMemo<SynapseApi | null>(
    () =>
      synapseUrl && musicbrainzAuth
        ? createSynapseApi(
            synapseUrl,
            () => musicbrainzAuth.access_token,
            musicbrainzAuth.refreshMBToken
          )
        : null,
    [synapseUrl, musicbrainzAuth]
  );
  // null hides the bell: the user's token can't read the inbox, or Synapse is unreachable.
  const [count, setCount] = React.useState<number | null>(null);
  const [notifications, setNotifications] = React.useState<
    InboxNotification[]
  >();

  React.useEffect(() => {
    api?.unreadCount().then(setCount, () => setCount(null));
  }, [api]);

  if (!api || count === null) {
    return null;
  }

  const onToggle = async (show: boolean) => {
    if (!show) return;
    try {
      setNotifications(await api.list(LIST_LIMIT));
    } catch {
      setNotifications([]);
    }
  };

  const markRead = (n: InboxNotification) => {
    if (n.read_at) return;
    api.markRead(n.id).catch(() => {});
    setCount((c) => Math.max((c ?? 1) - 1, 0));
  };

  const markAllRead = async () => {
    await api.markAllRead();
    setCount(0);
    const now = new Date().toISOString();
    setNotifications((list) =>
      list?.map((n) => ({ ...n, read_at: n.read_at ?? now }))
    );
  };

  const items = notifications
    ?.map((n) => ({ n, rendered: render(n) }))
    .filter((item) => item.rendered !== null);

  return (
    <Dropdown onToggle={onToggle} align="end">
      <Dropdown.Toggle
        variant="link"
        className="position-relative text-reset"
        aria-label={`Notifications, ${count} unread`}
      >
        <FontAwesomeIcon icon={faBell} />
        {count > 0 && (
          <span className="position-absolute top-0 start-100 translate-middle badge rounded-pill bg-danger">
            {count > 99 ? "99+" : count}
          </span>
        )}
      </Dropdown.Toggle>
      <Dropdown.Menu
        className="py-0 overflow-auto"
        style={{ width: "min(22rem, 90vw)", maxHeight: "70vh" }}
      >
        <div className="d-flex justify-content-between align-items-center gap-3 px-3 py-2 border-bottom">
          <strong>Notifications</strong>
          <button
            type="button"
            className="btn btn-link btn-sm p-0"
            onClick={markAllRead}
            disabled={count === 0}
          >
            Mark all read
          </button>
        </div>
        {!items && (
          <Dropdown.ItemText className="text-muted">Loading…</Dropdown.ItemText>
        )}
        {items?.length === 0 && (
          <Dropdown.ItemText className="text-muted">
            No notifications
          </Dropdown.ItemText>
        )}
        {items?.map(({ n, rendered }) => (
          <Dropdown.Item
            key={n.id}
            href={rendered?.href}
            onClick={() => markRead(n)}
            className={`text-wrap border-bottom py-2 ${
              n.read_at ? "" : "bg-body-secondary"
            }`}
          >
            <div>{rendered?.text}</div>
            <small className="text-muted">
              {preciseTimestamp(n.created_at, "timeAgo")}
            </small>
          </Dropdown.Item>
        ))}
      </Dropdown.Menu>
    </Dropdown>
  );
}
