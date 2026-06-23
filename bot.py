import re, requests
from telethon import TelegramClient, events

API_ID = 38455364
API_HASH = "d52e2859fb89e9b27a8217e32b55d3b8"
PHONE_NUMBER = "+919579179596"
SOURCE_CHANNELS = ["loot_deals_amazon_flipkart2"]
TARGET_CHANNEL = "lootbazaar7777"
AMAZON_AFFILIATE_TAG = "lootbazar064-21"

client = TelegramClient("lootalert_session", API_ID, API_HASH)
AMAZON_URL_RE = re.compile(r"https?://(?:www\.)?amazon\.in/[^\s]+")
AMAZON_SHORT_RE = re.compile(r"https?://amzn\.to/[^\s]+")
ASIN_RE = re.compile(r"/(?:dp|gp/product)/([A-Z0-9]{10})")

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
    if not text: return text
    text = AMAZON_SHORT_RE.sub(lambda m: rebuild_amazon_link(m.group(0)), text)
    text = AMAZON_URL_RE.sub(lambda m: rebuild_amazon_link(m.group(0)), text)
    return text

@client.on(events.NewMessage(chats=SOURCE_CHANNELS))
async def handler(event):
    new_text = swap_links(event.message.text or "")
    try:
        if event.message.media:
            await client.send_file(TARGET_CHANNEL, event.message.media, caption=new_text)
        else:
            await client.send_message(TARGET_CHANNEL, new_text)
        print("[OK] Reposted!")
    except Exception as e:
        print(f"[ERROR] {e}")

print("Bot starting... Watching:", SOURCE_CHANNELS)
with client:
    client.run_until_disconnected()
