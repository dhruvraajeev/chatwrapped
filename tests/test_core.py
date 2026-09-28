import unittest

from chatwrapped import messages


class MessagesTest(unittest.TestCase):
    def test_text_hidden_in_attributed_body(self):
        body = bytes.fromhex("4E53537472696E67019484012B0B") + b"hello there"
        self.assertEqual(messages.message_text(None, body), "hello there")

    def test_attachment_placeholder_is_removed(self):
        self.assertEqual(messages.message_text("pic \ufffc", None), "pic")

    def test_dates_in_seconds_or_nanoseconds(self):
        self.assertEqual(messages.to_unix(0), messages.APPLE_EPOCH)
        self.assertEqual(messages.to_unix(780000000), messages.to_unix(780000000 * 10**9))


if __name__ == "__main__":
    unittest.main()
