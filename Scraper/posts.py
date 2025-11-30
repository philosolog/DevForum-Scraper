import aiohttp
import asyncio
from typing import Dict, List, Tuple
from config import BASE_URL, POSTS_URL

async def fetch_topic_json(session: aiohttp.ClientSession, url: str, timeout: int = 10) -> Dict:
    if not url.endswith(".json"):
        if url.endswith("/"):
            url = url + ".json"
        else:
            url = url + ".json"
    async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
        resp.raise_for_status()
        return await resp.json()

async def collect_topic_posts(session: aiohttp.ClientSession, topic_json: Dict) -> List[Dict]:
    posts: List[Dict] = []
    topic_id = topic_json.get("id")
    post_stream = topic_json.get("post_stream", {})
    all_post_ids = post_stream.get("stream", [])
    if not all_post_ids:
        all_post_ids = [p.get("id") for p in post_stream.get("posts", [])]
    if all_post_ids:
        posts_ids_params = "&".join([f"post_ids[]={pid}" for pid in all_post_ids])
        posts_json_url = POSTS_URL.format(post_id=topic_id, posts_ids=posts_ids_params)
        try:
            async with session.get(posts_json_url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                posts_data = await resp.json()
                for p in posts_data.get("post_stream", {}).get("posts", []):
                    posts.append(
                        {
                            "post_id": p.get("id"),
                            "topic_id": topic_id,
                            "post_number": p.get("post_number"),
                            "username": p.get("username"),
                            "name": p.get("name"),
                            "created_at": p.get("created_at"),
                            "cooked": p.get("cooked"),
                            "url": posts_json_url,
                        }
                    )
        except Exception as e:
            print(f"  Warning: Failed to fetch all posts for topic {topic_id}: {e}")
            for p in post_stream.get("posts", []):
                posts.append(
                    {
                        "post_id": p.get("id"),
                        "topic_id": topic_id,
                        "post_number": p.get("post_number"),
                        "username": p.get("username"),
                        "name": p.get("name"),
                        "created_at": p.get("created_at"),
                        "cooked": p.get("cooked"),
                        "url": posts_json_url,
                    }
                )
    return posts

async def process_topic(semaphore: asyncio.Semaphore, session: aiohttp.ClientSession, topic: str) -> Tuple[List[Dict], Dict]:
    async with semaphore:
        try:
            print(f"Fetching: {topic}")
            topic_json = await fetch_topic_json(session, BASE_URL + topic)
            posts = await collect_topic_posts(session, topic_json)
            topic_meta = {
                "topic_id": topic_json.get("id"),
                "slug": topic_json.get("slug"),
                "title": topic_json.get("title"),
                "url": BASE_URL + topic,
                "created_at": topic_json.get("created_at"),
            }
            return posts, topic_meta
        except Exception as error:
            print(f"Error processing {topic}: {error}")
            return [], {"topic_id": None, "slug": None, "title": None, "url": BASE_URL + topic, "created_at": None}
