import re, requests, os
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.errors import UserAlreadyParticipantError, SessionPasswordNeededError
from telethon.tl.functions.messages import ImportChatInviteRequest, CheckChatInviteRequest

API_ID = 38455364
API_HASH = "d52e2859fb89e9b27a8217e32b55d3b8"
PHONE_NUMBER = "+919579179596"

SESSION_STRING = os.environ.get("SESSION_STRING", "").strip()
TELEGRAM_CODE = os.environ.get("TELEGRAM_CODE", "").strip()

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

async def main():
    client = None

    # Try existing session string first
    if SESSION_STRING:
        try:
            client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
            await client.connect()
            if await client.is_user_authorized():
                print("[OK] Logged in with SESSION_STRING")
            else:
                raise Exception("Not authorized")
        except Exception as e:
            print(f"[WARN] SESSION_STRING failed: {e}")
            client = None

    # Fresh login
    if client is None:
        temp = TelegramClient(StringSession(), API_ID, API_HASH)
        await temp.connect()

        if not TELEGRAM_CODE:
            # Send OTP to phone
            try:
                await temp.send_code_request(PHONE_NUMBER)
                print("[OK] OTP code sent to your Telegram app!")
                print("[ACTION] Check Telegram on your phone, get the code")
                print("[ACTION] Go to Railway Variables → Add TELEGRAM_CODE = (your code)")
                print("[ACTION] Then redeploy and the bot will login!")
            except Exception as e:
                print(f"[ERROR] Could not send OTP: {e}")
            await temp.disconnect()
            return

        # Use the provided code to login
        try:
            await temp.send_code_request(PHONE_NUMBER)
            await temp.sign_in(PHONE_NUMBER, TELEGRAM_CODE)
            new_session = temp.session.save()
            print("\n" + "="*60)
            print("LOGIN SUCCESS! Copy this and set as SESSION_STRING in Railway:")
            print(new_session)
            print("="*60)
            print("Also DELETE TELEGRAM_CODE variable after saving SESSION_STRING!")
            client = temp
        except Exception as e:
            print(f"[ERROR] Login failed: {e}")
            await temp.disconnect()
            return

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
