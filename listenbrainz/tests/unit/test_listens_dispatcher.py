import json
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from listenbrainz.websockets.listens_dispatcher import ListensDispatcher


class ListensDispatcherTestCase(unittest.TestCase):

    def setUp(self):
        self.app = SimpleNamespace(config={
            "UNIQUE_EXCHANGE": "unique",
            "PLAYING_NOW_EXCHANGE": "playing_now",
            "WEBSOCKETS_QUEUE": "follow_list",
            "PLAYING_NOW_QUEUE": "playing_now",
        }, logger=Mock())
        self.socketio = Mock()
        self.dispatcher = ListensDispatcher(self.app, self.socketio)

    def make_listens(self, count, user_name="listener"):
        return [{
            "user_id": 1,
            "user_name": user_name,
            # Descending timestamps verify that the last *received* listens win,
            # regardless of when they were listened to.
            "timestamp": 1700000000 - index,
            "recording_msid": "00000000-0000-0000-0000-000000000001",
            "track_metadata": {
                "artist_name": "Artist",
                "track_name": f"Track {index}",
                "additional_info": {},
            },
        } for index in range(count)]

    def send_listens(self, listens, event_name="listen"):
        message = Mock(body=json.dumps(listens))
        self.dispatcher.send_listens(event_name, message)
        message.ack.assert_called_once_with()

    def assert_emitted(self, expected, event_name="listen"):
        calls = self.socketio.emit.call_args_list
        self.assertEqual(len(calls), len(expected))
        for call, data in zip(calls, expected):
            self.assertEqual(call.args[0], event_name)
            self.assertEqual(call.kwargs, {"to": data["user_name"]})
            payload = json.loads(call.args[1])
            self.assertEqual(payload["track_metadata"], data["track_metadata"])
            if event_name == "listen":
                self.assertEqual(payload["listened_at"], data["timestamp"])

    def test_buffers_latest_submissions_per_user_across_batches(self):
        listens = self.make_listens(25)
        other_listens = self.make_listens(3, user_name="another_listener")
        self.send_listens(listens[:12])
        self.send_listens(other_listens)
        self.send_listens(listens[12:])

        self.socketio.emit.assert_not_called()
        self.assertEqual(len(self.dispatcher.pending_listens["listener"]), 10)
        self.assertEqual(len(self.dispatcher.pending_listens["another_listener"]), 3)

        self.dispatcher.flush_listens()
        self.assert_emitted(listens[-10:] + other_listens)
        self.assertEqual(self.dispatcher.pending_listens, {})

        # An empty flush must not resend notifications or retain idle users.
        self.socketio.reset_mock()
        self.dispatcher.flush_listens()
        self.socketio.emit.assert_not_called()
        self.assertEqual(self.dispatcher.pending_listens, {})

    def test_arrivals_during_flush_wait_for_next_flush(self):
        listens = self.make_listens(3)
        self.send_listens(listens[:1])
        self.socketio.emit.side_effect = lambda *args, **kwargs: self.send_listens(listens[1:])

        self.dispatcher.flush_listens()
        self.assert_emitted(listens[:1])

        self.socketio.emit.side_effect = None
        self.dispatcher.flush_listens()
        self.assert_emitted(listens)
        self.assertEqual(self.dispatcher.pending_listens, {})

    def test_playing_now_is_immediate(self):
        listens = self.make_listens(1)
        del listens[0]["timestamp"]
        self.send_listens(listens, event_name="playing_now")
        self.assert_emitted(listens, event_name="playing_now")
        self.assertEqual(self.dispatcher.pending_listens, {})

    def test_emit_failure_does_not_stop_later_notifications(self):
        listens = self.make_listens(3)
        self.send_listens(listens[:2])
        self.socketio.emit.side_effect = [RuntimeError("Socket unavailable"), None]

        self.dispatcher.flush_listens()
        self.assertEqual(self.socketio.emit.call_count, 2)
        self.app.logger.exception.assert_called_once()
        self.assertEqual(self.dispatcher.pending_listens, {})

        self.socketio.reset_mock(side_effect=True)
        self.send_listens(listens[2:])
        self.dispatcher.flush_listens()
        self.assert_emitted(listens[2:])
