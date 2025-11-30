import asyncio
import aiohttp
from config import BASE_URL, CATEGORY_URL, CONCURRENT_REQUESTS, DATASET_DB
from topics import collect_category_topics
from posts import process_topic
from database import save_posts, save_topic

async def main_async() -> None:
    semaphore = asyncio.Semaphore(CONCURRENT_REQUESTS)
    async with aiohttp.ClientSession() as session:
        topics = await collect_category_topics(session, CATEGORY_URL)
        tasks = [process_topic(semaphore, session, topic) for topic in topics]
        results = await asyncio.gather(*tasks)
        total = 0
        for posts, topic_meta in results:
            if topic_meta.get("topic_id") is not None:
                save_topic(topic_meta)
            inserted = save_posts(posts)
            total += inserted
            print(f"Saved {inserted} posts for topic {topic_meta.get('topic_id')} into {DATASET_DB}")
            await asyncio.sleep(0.2)
        print(f"Done. Total posts processed: {total}")

if __name__ == "__main__":
    asyncio.run(main_async())
