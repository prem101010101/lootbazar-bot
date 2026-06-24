import re, requests, os, base64, struct, sqlite3
from telethon import TelegramClient, events
from telethon.errors import UserAlreadyParticipantError
from telethon.tl.functions.messages import ImportChatInviteRequest, CheckChatInviteRequest

API_ID = 38455364
API_HASH = "d52e2859fb89e9b27a8217e32b55d3b8"

SESSION_STRING = os.environ.get("SESSION_STRING", "").strip()

PUBLIC_CHANNELS = [
    "loot_deals_amazon_flipkart2",
    "Loot_DealsX",
]
PRIVATE_INVITES = [
    "kTvbwlaPbH1mM2E1",
    "sX1Ht4p33nFjZDE1",
    "AAAAAFZ4xgGd0u8r66YAGg",
]
TARGET_CHANNEL = "lootbazaar7777"
AMAZON_AFFILIATE_TAG = "lootbazar064-21"

AMAZON_URL_RE = re.compile(r'https?://(?:www\.)?amazon\.in/[^\s]+')
AMAZON_SHORT_RE = re.compile(r'https?://amzn\.to/[^\s]+')
ASIN_RE = re.compile(r'/(?:dp|gp/product)/([A-Z0-9]{10})')

def resolve_short_link(url):
    try:
        r = requests.head(url, allow_redirects=True, timeout=8)
        return r.url
    except:
        return url

def rebuild_amazon_link(url):
    full = resolve_short_link(url) if "amzn.to" in url else url
    m = ASIN_RE.search(full)
    if m:
        return f"https://www.amazon.in/dp/{m.group(1)}?tag={AMAZON_AFFILIATE_TAG}"
    return url

def swap_links(text):
    if not text:
        return text
    text = AMAZON_SHORT_RE.sub(lambda m: rebuild_amazon_link(m.group(0)), text)
    text = AMAZON_URL_RE.sub(lambda m: rebuild_amazon_link(m.group(0)), text)
    return text

def create_session_file(session_str, path="bot.session"):
    """Manually decode session string and create SQLite session file."""
    try:
        raw = session_str[1:]  # Remove version byte
        raw = raw.rstrip("=")
        padding = (4 - len(raw) % 4) % 4
        data = base64.urlsafe_b64decode(raw + "=" * padding)

        if len(data) == 263:
            dc_id, ip_bytes, port, auth_key = struct.unpack('>B4sH256s', data)
            ip = '.'.join(str(b) for b in ip_bytes)
        elif len(data) == 275:
            dc_id, ip_bytes, port, auth_key = struct.unpack('>B16sH256s', data)
            ip = ':'.join(format(b, '02x') for b in ip_bytes)
        else:
            print(f"[WARN] Unknown session size: {len(data)} bytes")
            return False

        conn = sqlite3.connect(path)
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS version (version integer primary key)")
        c.execute("INSERT OR REPLACE INTO version VALUES (7)")
        c.execute("CREATE TABLE IF NOT EXISTS sessions (dc_id integer, server_address text, port integer, auth_key blob, takeout_id integer, primary key (dc_id))")
        c.execute("DELETE FROM sessions")
        c.execute("INSERT INTO sessions VALUES (?, ?, ?, ?, ?)", (dc_id, ip, port, auth_key, None))
        c.execute("CREATE TABLE IF NOT EXISTS entities (id integer, hash integer, username text, phone integer, name text, date integer, primary key (id))")
        c.execute("CREATE TABLE IF NOT EXISTS sent_files (md5_digest blob, file_size integer, type integer, id integer, hash integer, primary key (md5_digest, file_size, type))")
        c.execute("CREATE TABLE IF NOT EXISTS update_state (id integer, pts integer, qts integer, date integer, seq integer, primary key (id))")
        conn.commit()
        conn.close()
        print(f"[OK] Session created: dc_id={dc_id}, ip={ip}, port={port}")
        return True
    except Exception as e:
        print(f"[ERROR] Session creation failed: {e}")
        return False

async def main():
    if not SESSION_STRING:
        print("[ERROR] No SESSION_STRING set in Railway Variables!")
        return

    if not create_session_file(SESSION_STRING, "bot.session"):
        print("[ERROR] Could not create session file!")
        return

    client = TelegramClient("bot", API_ID, API_HASH)
    await client.connect()

    if not await client.is_user_authorized():
        print("[ERROR] Session not authorized — it may be expired")
        return

    print("[OK] Logged in successfully!")
    source_entities = []

    for username in PUBLIC_CHANNELS:
        try:
            entity = await client.get_entity(username)
            source_entities.append(entity)
            print(f"[OK] Watching: @{username}")
        except Exception as e:
            print(f"[WARN] @{username}: {e}")

    for invite_hash in PRIVATE_INVITES:
        try:
            result = await client(ImportChatInviteRequest(invite_hash))
            entity = result.chats[0]
            source_entities.append(entity)
            print(f"[OK] Joined: {entity.title}")
        except UserAlreadyParticipantError:
            try:
                info = await client(CheckChatInviteRequest(invite_hash))
                if hasattr(info, 'chat'):
                    source_entities.append(info.chat)
                    print(f"[OK] Already in: {info.chat.title}")
            except Exception as e:
                print(f"[WARN] {e}")
        except Exception as e:
            print(f"[WARN] {invite_hash[:8]}...: {e}")

    if not source_entities:
        print("[ERROR] No source channels found!")
        return

    @client.on(events.NewMessage(chats=source_entities))
    async def handler(event):
        new_text = swap_links(event.message.text or "")
        try:
            if event.message.media:
                await client.send_file(TARGET_CHANNEL, event.message.media, caption=new_text)
            elif new_text:
                await client.send_message(TARGET_CHANNEL, new_text)
            print("[OK] Reposted!")
        except Exception as e:
            print(f"[ERROR] {e}")

    print(f"\nBot running! Watching {len(source_entities)} channels → @{TARGET_CHANNEL}")
    await client.run_until_disconnected()

import asyncio
asyncio.run(main())
