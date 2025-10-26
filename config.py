# config.py
import os
# Telegram API credentials
APP_URL= "https://update.koyeb.app"
API_ID = 25198711
API_HASH = '2a99a1375e26295626c04b4606f72752'
BOT_TOKEN = os.getenv('BOT_TOKEN', '')
ADMINS = 1740287480, 5192808332, 7428552084, 5626835282, 1190642269, 1759377892
# File paths and messages
OWNER = 'OtakuFlix'
REPO = 'ADATA'
PATH = 'anime_data.txt'
MESSAGE = '♦️ DONE UPDATING ♦️'
GIT_TOKEN = os.getenv('GIT_TOKEN', '')

# API keys for different platforms
RPMSHARE_API_KEY = 'b57f6ad44bf1fb528c57ea90'
FILEMOON_API_KEY = '42605q5ytvlhmu9eris67'
ANIFLIX_USER_ID = '1740287480'

# URLs for fetching data
PLATFORMS = {
    'Filemoon': f'https://filemoon-api.vercel.app/api/filemoon?key={FILEMOON_API_KEY}&fld_id=0',
    'RpmShare': f'https://rpmshare.com/api/folder/list?key={RPMSHARE_API_KEY}&fld_id=0',
    'Aniflix': f'https://aniflix.koyeb.app/api/folder_list?user_id={ANIFLIX_USER_ID}&page=1&page_size=200'
}

API_URLS = {
    'Kitsu': 'https://kitsu.io/api/edge/genres',
    'JikanV4': 'https://api.jikan.moe/v4/anime/1',
}

# Keep-alive settings
KEEP_ALIVE_INTERVAL = 120  # Ping every 2 minutes
HEALTH_CHECK_PORT = 8000
