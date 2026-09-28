"""Look up names for phone numbers and emails in your Contacts."""
import glob
import json
import os
import re
import sqlite3

from .messages import open_readonly

CONTACTS = os.path.expanduser("~/Library/Application Support/AddressBook/**/*.abcddb")
ALIASES_FILE = os.path.expanduser("~/.config/chatwrapped/aliases.json")


def normalize(handle):
    """'+1 (512) 555-0101' and '5125550101' both become '5125550101'. Emails get lowercased."""
    if "@" in handle:
        return handle.lower()
    digits = re.sub(r"\D", "", handle)
    return digits[-10:] if len(digits) >= 7 else handle.lower()


def load_contacts():
    names = {}
    for path in glob.glob(CONTACTS, recursive=True):
        try:
            names.update(read_address_book(path))
        except sqlite3.Error:
            pass  # can't read this address book, so those people just show up as numbers
    return names


def read_address_book(path):
    db = open_readonly(path)

    people = {}
    for person_id, first, last, nickname in db.execute(
            "select Z_PK, ZFIRSTNAME, ZLASTNAME, ZNICKNAME from ZABCDRECORD"):
        full_name = " ".join(part for part in (first, last) if part)
        people[person_id] = full_name or nickname

    names = {}
    for person_id, handle in db.execute("""
        select ZOWNER, ZFULLNUMBER from ZABCDPHONENUMBER
        union all
        select ZOWNER, ZADDRESS from ZABCDEMAILADDRESS
    """):
        if handle and people.get(person_id):
            names[normalize(handle)] = people[person_id]
    return names


def load_aliases(path=ALIASES_FILE):
    """aliases.json looks like {"+15125550101": "Sam", "sam.alt@icloud.com": "Sam"}."""
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return {normalize(handle): name for handle, name in json.load(f).items()}
