import unittest

from chatwrapped import messages
from chatwrapped import contacts


class MessagesTest(unittest.TestCase):
    def test_text_hidden_in_attributed_body(self):
        body = bytes.fromhex("4E53537472696E67019484012B0B") + b"hello there"
        self.assertEqual(messages.message_text(None, body), "hello there")

    def test_attachment_placeholder_is_removed(self):
        self.assertEqual(messages.message_text("pic \ufffc", None), "pic")

    def test_dates_in_seconds_or_nanoseconds(self):
        self.assertEqual(messages.to_unix(0), messages.APPLE_EPOCH)
        self.assertEqual(messages.to_unix(780000000), messages.to_unix(780000000 * 10**9))


class ContactsTest(unittest.TestCase):
    def test_phone_number_formats_match(self):
        self.assertEqual(contacts.normalize("+1 (512) 555-0101"), contacts.normalize("5125550101"))

    def test_emails_are_lowercased(self):
        self.assertEqual(contacts.normalize("Sam@iCloud.com"), "sam@icloud.com")

    def test_missing_aliases_file(self):
        self.assertEqual(contacts.load_aliases("/nonexistent/aliases.json"), {})


if __name__ == "__main__":
    unittest.main()
