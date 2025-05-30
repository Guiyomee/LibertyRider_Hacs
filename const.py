"""Constants for the Liberty Rider integration."""
DOMAIN = "liberty_rider"
DEFAULT_NAME = "Liberty Rider"
BASE_URL = "https://rider.live"
API_URL = "https://api.liberty-rider.com/graphql"

CONF_SHARE_URL = "share_url"
CONF_LANGUAGE = "language"
CONF_SCAN_INTERVAL = "scan_interval"

LANGUAGES = {
    "fr": "Français",
    "en": "English",
    "es": "Español / SOON",
    "de": "Deutsch / SOON"
}

DEFAULT_LANGUAGE = "fr"
DEFAULT_SCAN_INTERVAL = 5  # minutes
MIN_SCAN_INTERVAL = 1  # minute
MAX_SCAN_INTERVAL = 60  # minutes

