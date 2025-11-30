BASE_URL = "https://devforum.roblox.com"
CATEGORY_URL_TEMPLATE = "/c/updates/announcements/36.json?ascending=false&no_definitions=true&{page}"
CATEGORY_URL = BASE_URL + CATEGORY_URL_TEMPLATE
POSTS_URL = BASE_URL + "/t/{post_id}/posts.json?{posts_ids}&include_suggested=true"
EXCLUDED_TOPICS = set()
MAX_TOPICS = 10
CONCURRENT_REQUESTS = 3
DATASET_DB = "dataset.db"
