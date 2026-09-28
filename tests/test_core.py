import unittest

from chatwrapped import messages
from chatwrapped import contacts
from chatwrapped import reactions
from chatwrapped.cli import build_data, find_chat, render_html


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


class ReactionsTest(unittest.TestCase):
    def test_latest_reaction_wins(self):
        events = [
            (1, "a", 2003, None), (1, "a", 3003, None),  # laugh, then taken back
            (2, "a", 2006, "😂"),                         # emoji laugh
            (3, "a", 2000, None),                         # heart
            (4, "b", 2003, None), (4, "b", 2000, None),  # laugh changed to heart
            (5, "b", 2000, None), (5, "b", 2006, "💀"),  # heart changed to skull
            (6, "b", 2003, None), (6, "b", 2006, "🔥"),  # laugh changed to an emoji we don't track
        ]
        expected = {
            (2, "a"): reactions.LAUGH,
            (3, "a"): reactions.HEART,
            (4, "b"): reactions.HEART,
            (5, "b"): reactions.SKULL,
        }
        self.assertEqual(reactions.final_reactions(events), expected)


class BuildDataTest(unittest.TestCase):
    # (guid, sender, time, text, reaction_type, reacted_to, emoji); a sender of None means me
    ROWS = [
        ("m1", "+15125550101", 100, "joke", 0, None, None),
        ("m2", None, 200, "</script><b>hi", 0, None, None),
        ("r1", None, 300, "", 2006, "p:0/m1", "💀"),              # I skull Sam's joke
        ("r2", "sam@icloud.com", 400, "", 2003, "p:0/m1", None),  # Sam laughs at his own joke (ignored)
        ("r3", "+15125550101", 500, "", 2000, "p:0/m2", None),    # Sam hearts my message
    ]
    NAMES = {"5125550101": "Sam", "sam@icloud.com": "Sam"}

    def test_build_data(self):
        data = build_data("chat", self.ROWS, self.NAMES)
        self.assertEqual(data["people"], ["Sam", "Me"])
        self.assertEqual(data["msgs"], [[0, 100, 4], [1, 200, 14]])
        self.assertEqual(sorted(data["reacts"]), [[0, 1, reactions.HEART], [1, 0, reactions.SKULL]])
        self.assertEqual(data["texts"], {0: "joke", 1: "</script><b>hi"})

    def test_hide_text(self):
        data = build_data("chat", self.ROWS, self.NAMES, hide_text=True)
        self.assertEqual(set(data["texts"].values()), {"(text hidden)"})

    def test_message_cannot_break_out_of_the_script_tag(self):
        html = render_html(build_data("chat", self.ROWS, self.NAMES))
        self.assertNotIn("/*DATA*/null", html)
        self.assertNotIn("</script><b>", html)


class FindChatTest(unittest.TestCase):
    CHATS = [(50, "the squad", 9), (7, "+15125550101, Sam", 5), (8, "squad club", 3)]

    def test_exact_name_then_id_then_part_of_name(self):
        self.assertEqual(find_chat(self.CHATS, "The Squad")[0], 50)
        self.assertEqual(find_chat(self.CHATS, "50")[0], 50)  # the id wins over the "50" in a phone number
        self.assertEqual(find_chat(self.CHATS, "club")[0], 8)

    def test_ambiguous_name_exits(self):
        with self.assertRaises(SystemExit):
            find_chat(self.CHATS, "squad")


if __name__ == "__main__":
    unittest.main()
