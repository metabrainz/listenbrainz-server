import * as React from "react";
import { Dropdown } from "react-bootstrap";
import DOMPurify from "dompurify";
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

// A plain link, so the toggle looks like the other sidebar nav links.
const NavToggle = React.forwardRef<
  HTMLAnchorElement,
  React.AnchorHTMLAttributes<HTMLAnchorElement>
>(function NavToggle({ onClick, children, ...props }, ref) {
  return (
    <a
      ref={ref}
      href="#notifications"
      role="button"
      onClick={(e) => {
        e.preventDefault();
        onClick?.(e);
      }}
      {...props}
    >
      {children}
    </a>
  );
});

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
  const [error, setError] = React.useState<string>();

  React.useEffect(() => {
    api?.unreadCount().then(setCount, () => setCount(null));
  }, [api]);

  if (!api || count === null) {
    return null;
  }

  const onToggle = async (show: boolean) => {
    if (!show) return;
    setError(undefined);
    try {
      const [list, unread] = await Promise.all([
        api.list(LIST_LIMIT),
        api.unreadCount(),
      ]);
      setNotifications(list);
      setCount(unread);
    } catch {
      setError("Couldn't load notifications, try again later.");
    }
  };

  // Only update the badge and list once Synapse has the change.
  const update = async (change: Promise<void>, ids?: number[]) => {
    try {
      await change;
    } catch {
      setError("Couldn't update notifications, try again later.");
      return;
    }
    const now = new Date().toISOString();
    setNotifications((list) =>
      list?.map((n) =>
        !ids || ids.includes(n.id) ? { ...n, read_at: n.read_at ?? now } : n
      )
    );
    setCount((c) => (ids ? Math.max((c ?? 1) - ids.length, 0) : 0));
  };

  const markRead = (n: InboxNotification) =>
    !n.read_at && update(api.markRead(n.id), [n.id]);
  const markAllRead = () => update(api.markAllRead());

  const items = notifications
    ?.map((n) => ({ n, rendered: render(n) }))
    .filter((item) => item.rendered !== null);

  return (
    // Opens beside the sidebar, where there is room for the list.
    <Dropdown onToggle={onToggle} drop="end">
      <Dropdown.Toggle
        as={NavToggle}
        aria-label={`Notifications, ${count} unread`}
      >
        Notifications
        {count > 0 && (
          <span className="badge rounded-pill bg-danger ms-1">
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
        {error && (
          <Dropdown.ItemText className="text-danger">{error}</Dropdown.ItemText>
        )}
        {!items && !error && (
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
            // A message can hold its own links, which can't sit inside another link.
            as={rendered?.href ? "a" : "div"}
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
