# config.py
import os
# Telegram API credentials
API_ID = 25198711
API_HASH = '2a99a1375e26295626c04b4606f72752'
BOT_TOKEN = '7096468759:AAFt7RTlnBwNHRJA1fQC0a4TayXKaEubVGs'
ADMINS = 1740287480, 5192808332, 7428552084, 5626835282, 1190642269
# File paths and messages
OWNER = 'OtakuFlix'
REPO = 'ADATA'
PATH = 'anime_data.txt'
MESSAGE = '♦️ DONE UPDATING ♦️'
GIT_TOKEN = os.getenv('GIT_TOKEN', '')

# API keys for different platforms
RPMSHARE_API_KEY = 'b57f6ad44bf1fb528c57ea90'
FILEMOON_API_KEY = '42605q5ytvlhmu9eris67'


# URLs for fetching data
PLATFORMS = {
    'Filemoon': f'https://filemoon-api.vercel.app/api/filemoon?key={FILEMOON_API_KEY}&fld_id=0',
    'RpmShare': f'https://rpmshare.com/api/folder/list?key={RPMSHARE_API_KEY}&fld_id=0'
}

API_URLS = {
    'Kitsu': 'https://kitsu.io/api/edge/genres',  # Example Kitsu API endpoint
    'JikanV4': 'https://api.jikan.moe/v4/anime/1',  # Example JikanV4 API endpoint
}
