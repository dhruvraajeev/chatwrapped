"""Work out each person's final reaction on each message."""

CATEGORIES = ["laugh", "skull", "sob", "heart"]
LAUGH, SKULL, SOB, HEART = range(4)

EMOJI_CATEGORY = {
    "😂": LAUGH, "🤣": LAUGH, "😹": LAUGH,
    "💀": SKULL, "☠️": SKULL,
    "😭": SOB,
    "❤️": HEART, "❤": HEART, "🫶": HEART,
}

# Reaction types in chat.db: 2000-2007 add a reaction, 3000-3007 take it back.
LOVE = 2000
HAHA = 2003
EMOJI = 2006


def category(reaction_type, emoji):
    """The category a reaction counts toward, or None if we don't track it (👍, 🔥, ...)."""
    if reaction_type == EMOJI:
        return EMOJI_CATEGORY.get(emoji)
    if reaction_type == HAHA:
        return LAUGH
    if reaction_type == LOVE:
        return HEART
    return None


def final_reactions(events):
    """events are (person, message_guid, reaction_type, emoji), oldest first.
    Returns {(person, message_guid): category}.

    Everyone gets one reaction per message, so a new one replaces the old one
    and taking it back clears it."""
    current = {}
    for person, guid, reaction_type, emoji in events:
        if 2000 <= reaction_type < 3000:
            current[(person, guid)] = category(reaction_type, emoji)
        elif 3000 <= reaction_type < 4000:
            current.pop((person, guid), None)
    return {key: cat for key, cat in current.items() if cat is not None}
