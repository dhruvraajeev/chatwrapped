"""Make a reactions dashboard for one of your iMessage group chats."""
import argparse
import json
import os
import re
import subprocess
import sys
from importlib import resources

from . import contacts, messages, reactions

OUTPUT_DIR = os.path.expanduser("~/ChatWrapped")
FULL_DISK_ACCESS = "x-apple.systempreferences:com.apple.preference.security?Privacy_AllFiles"


def build_data(chat_name, rows, names, hide_text=False):
    """Turns the rows from messages.read_chat() into the data the dashboard uses."""
    people = []  # display names; everything below refers to people by their index in this list

    def person_index(handle):
        name = "Me" if handle is None else names.get(contacts.normalize(handle), handle)
        if name not in people:
            people.append(name)
        return people.index(name)

    msgs = []       # [sender, unix_time, length]
    texts = []
    msg_index = {}  # message guid -> position in msgs
    events = []     # every reaction, in order

    for guid, sender, when, text, reaction_type, target, emoji in rows:
        who = person_index(sender)
        if reaction_type == 0:
            msg_index[guid] = len(msgs)
            msgs.append([who, when, len(text)])
            texts.append(text)
        elif target:
            # target looks like "p:0/<guid>" or "bp:<guid>"
            target_guid = target.split("/")[-1].removeprefix("bp:")
            events.append((who, target_guid, reaction_type, emoji))

    reacts = []  # [reactor, message index, category]
    for (reactor, guid), category in reactions.final_reactions(events).items():
        i = msg_index.get(guid)
        if i is None or msgs[i][0] == reactor:
            continue  # message isn't in this chat, or someone reacted to their own message
        reacts.append([reactor, i, category])

    reacted = sorted({i for _, i, _ in reacts})
    return {
        "chat": chat_name,
        "people": people,
        "categories": reactions.CATEGORIES,
        "msgs": msgs,
        "reacts": reacts,
        "texts": {i: "(text hidden)" if hide_text else texts[i] for i in reacted},
    }


def render_html(data):
    template = resources.files("chatwrapped").joinpath("dashboard.html").read_text(encoding="utf-8")
    data_json = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    # Without this, a message containing "</script>" would end the script tag early.
    data_json = data_json.replace("</", "<\\/")
    return template.replace("/*DATA*/null", data_json, 1)


def chat_title(name, handles, names):
    """Unnamed group chats get a title made from the first few members."""
    if name:
        return name
    members = [names.get(contacts.normalize(handle), handle) for handle in handles]
    title = ", ".join(members[:4])
    if len(members) > 4:
        title += f" +{len(members) - 4}"
    return title or "(unnamed)"


def find_chat(chats, query):
    """Match the exact name first, then the chat id, then any part of the name."""
    q = query.lower()
    matches = [chat for chat in chats if chat[1].lower() == q]
    if not matches:
        matches = [chat for chat in chats if str(chat[0]) == query]
    if not matches:
        matches = [chat for chat in chats if q in chat[1].lower()]
    if len(matches) != 1:
        sys.exit(f"'{query}' matches {len(matches)} chats. Run `chatwrapped --list` and use the chat id instead.")
    return matches[0]


def pick_chat(chats):
    shown = chats[:30]
    for number, (_, title, count) in enumerate(shown, 1):
        print(f"{number:3}. {title[:44]:<44} {count:>9,} msgs")
    while True:
        answer = input(f"\nWhich chat? [1-{len(shown)}] ").strip()
        if answer.isdigit() and 1 <= int(answer) <= len(shown):
            return shown[int(answer) - 1]


def main(argv=None):
    parser = argparse.ArgumentParser(prog="chatwrapped", description=__doc__)
    parser.add_argument("chat", nargs="?", help="chat name (or part of it) or id; leave it out to pick from a list")
    parser.add_argument("--list", action="store_true", help="list every group chat with its id")
    parser.add_argument("-o", "--out", help=f"where to save the dashboard (default: {OUTPUT_DIR}/<chat>.html)")
    parser.add_argument("--hide-text", action="store_true", help="leave message text out, e.g. before sharing it")
    parser.add_argument("--aliases", default=contacts.ALIASES_FILE, help="JSON file of {handle: name} (default: %(default)s)")
    parser.add_argument("--no-open", action="store_true", help="don't open the dashboard when it's done")
    args = parser.parse_args(argv)

    if sys.platform != "darwin":
        sys.exit("chatwrapped reads the macOS Messages database, so it only works on a Mac.")

    try:
        db = messages.connect()
    except messages.NoAccess as e:
        print(f"Can't read your Messages database ({e}).\n\n"
              "Turn on Full Disk Access for your terminal app in System Settings → Privacy & Security\n"
              "→ Full Disk Access, then quit and reopen the terminal and try again.", file=sys.stderr)
        subprocess.run(["open", FULL_DISK_ACCESS])
        return 1

    names = contacts.load_contacts()
    names.update(contacts.load_aliases(args.aliases))

    chats = []
    for chat_id, name, count, handles in messages.list_group_chats(db):
        chats.append((chat_id, chat_title(name, handles, names), count))
    if not chats:
        sys.exit("No group chats found in Messages on this Mac.")

    if args.list:
        for chat_id, title, count in chats:
            print(f"{chat_id:6}  {title[:44]:<44} {count:>9,} msgs")
        return 0

    chat_id, title, _ = find_chat(chats, args.chat) if args.chat else pick_chat(chats)
    data = build_data(title, messages.read_chat(db, chat_id), names, args.hide_text)
    if not data["msgs"]:
        sys.exit(f"'{title}' has no messages on this Mac.")

    filename = re.sub(r"[^\w\- ]+", "", title).strip() or f"chat-{chat_id}"
    out = args.out or os.path.join(OUTPUT_DIR, filename + ".html")
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(render_html(data))

    print(f"{title}: {len(data['people'])} people, {len(data['msgs']):,} messages, {len(data['reacts']):,} reactions")
    print(f"Saved to {out}")
    if not args.no_open:
        subprocess.run(["open", out])
    return 0
