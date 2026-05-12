import aiohttp
from typing import List
from config import BASE_URL, CATEGORY_URL, EXCLUDED_TOPICS, MAX_TOPICS

async def collect_category_topics(session: aiohttp.ClientSession, category_url_template: str = CATEGORY_URL, max_topics: int = MAX_TOPICS) -> List[str]:
    topics: List[str] = []
    seen = set()
    page = 0
    while len(topics) < max_topics:
        page_param = f"page={page}"
        url = category_url_template.format(page=page_param)
        if not url.startswith("http"):
            url = BASE_URL + url
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                text = await resp.text()
                is_json = False
                try:
                    _json = await resp.json()
                    is_json = True
                except Exception:
                    _json = None
        except Exception:
            break
        if is_json and _json is not None:
            topic_list = _json.get("topic_list") or _json.get("topics") or {}
            candidates = []
            if isinstance(topic_list, dict):
                candidates = topic_list.get("topics", [])
            elif isinstance(topic_list, list):
                candidates = topic_list
            for t in candidates:
                _tid = t.get("id")
                _slug = t.get("slug")
                if not _tid:
                    continue
                if _slug:
                    path = f"/t/{_slug}/{_tid}"
                else:
                    path = f"/t/{_tid}"
                if path not in seen and path not in EXCLUDED_TOPICS:
                    seen.add(path)
                    topics.append(path)
                    if len(topics) >= max_topics:
                        break
        else:
            import re
            for m in re.finditer(r'href="(/t/[^"]+?/\d+)"', text):
                path = m.group(1)
                if path not in seen:
                    seen.add(path)
                    topics.append(path)
                    if len(topics) >= max_topics:
                        break
        page += 1
    return topics
