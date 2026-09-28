"""Read your group chats out of the macOS Messages database."""
import os
import sqlite3

CHAT_DB = os.path.expanduser("~/Library/Messages/chat.db")

# Messages stores dates as time since 2001-01-01 (in nanoseconds on newer macOS).
APPLE_EPOCH = 978307200


class NoAccess(Exception):
    """chat.db couldn't be read, usually because the terminal doesn't have Full Disk Access."""


def open_readonly(path):
    return sqlite3.connect(f"file:{path}?mode=ro", uri=True)


def connect(path=CHAT_DB):
    try:
        db = open_readonly(path)
        db.execute("select 1 from message limit 1")
    except sqlite3.Error as e:
        raise NoAccess(f"{path}: {e}") from e
    return db


def to_unix(date):
    if date > 1e11:
        date = date / 1e9
    return int(date + APPLE_EPOCH)


def message_text(text, attributed_body):
    # Newer macOS leaves `text` empty and keeps the text inside attributedBody instead.
    if text is None and attributed_body:
        text = decode_attributed_body(attributed_body)
    # U+FFFC is the placeholder Messages puts where an attachment was.
    return (text or "").replace("\ufffc", "").strip()


def decode_attributed_body(blob):
    start = blob.find(b"NSString")
    if start == -1:
        return None
    pos = start + len(b"NSString") + 5
    length = blob[pos]
    pos += 1
    # Long strings store their length in the next 2 or 4 bytes instead.
    if length == 0x81:
        length = int.from_bytes(blob[pos:pos + 2], "little")
        pos += 2
    elif length == 0x82:
        length = int.from_bytes(blob[pos:pos + 4], "little")
        pos += 4
    return blob[pos:pos + length].decode("utf-8", "replace")


def list_group_chats(db):
    """Returns [(chat_id, name, message_count, member_handles)], busiest chat first."""
    chats = db.execute("""
        select chat.ROWID, coalesce(chat.display_name, ''), count(*)
        from chat
        join chat_message_join on chat_message_join.chat_id = chat.ROWID
        where chat.style = 43  -- group chats
        group by chat.ROWID
        order by count(*) desc
    """).fetchall()

    members = {}
    for chat_id, handle in db.execute("""
        select chat_handle_join.chat_id, handle.id
        from chat_handle_join
        join handle on handle.ROWID = chat_handle_join.handle_id
    """):
        members.setdefault(chat_id, []).append(handle)

    return [(chat_id, name, count, members.get(chat_id, [])) for chat_id, name, count in chats]


def read_chat(db, chat_id):
    """Yields every message and reaction in a chat, oldest first, as
    (guid, sender, unix_time, text, reaction_type, reacted_to_guid, emoji).
    `sender` is None for messages you sent."""
    columns = {row[1] for row in db.execute("pragma table_info(message)")}
    # Emoji reactions only exist on macOS 14 and later.
    emoji = "message.associated_message_emoji" if "associated_message_emoji" in columns else "null"

    rows = db.execute(f"""
        select message.guid, message.is_from_me, handle.id, message.date, message.text,
               message.attributedBody, message.associated_message_type,
               message.associated_message_guid, {emoji}
        from message
        join chat_message_join on chat_message_join.message_id = message.ROWID
        left join handle on handle.ROWID = message.handle_id
        where chat_message_join.chat_id = ? and message.item_type = 0
        order by message.date
    """, (chat_id,))

    for guid, from_me, handle, date, text, body, reaction_type, target, emoji in rows:
        sender = None if from_me else (handle or "unknown")
        yield guid, sender, to_unix(date), message_text(text, body), reaction_type or 0, target, emoji
