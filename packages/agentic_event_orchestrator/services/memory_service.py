import logging

logger = logging.getLogger(__name__)


class MemoryService:
    def __init__(self, api_key: str):
        self.client = None
        if api_key:
            try:
                from mem0 import AsyncMemoryClient
                self.client = AsyncMemoryClient(api_key=api_key)
            except ImportError:
                logger.warning("mem0ai is not installed — memory features disabled")
            except Exception as e:
                logger.warning("Failed to initialise Mem0 client: %s — memory features disabled", e)
        else:
            logger.warning("No Mem0 API key provided — memory features disabled")

    async def get_user_memory(self, user_id: str) -> str:
        """Retrieve top-10 memories for a user as a plain-text block."""
        if self.client is None:
            return ""
        try:
            result = await self.client.get_all(filters={"user_id": user_id})
            # get_all returns a list of memory dicts directly
            memories = result if isinstance(result, list) else result.get("results", [])
            return "\n".join(m["memory"] for m in memories[:10] if m.get("memory"))
        except Exception as e:
            logger.warning("Mem0 get_all failed: %s", e)
            return ""

    async def update_user_memory(self, user_id: str, messages: list[dict]) -> None:
        """Persist a conversation turn (user + assistant messages) to Mem0."""
        if self.client is None:
            return
        try:
            await self.client.add(messages, user_id=user_id)
        except Exception as e:
            logger.warning("Mem0 add failed — skipping: %s", e)

    async def search_user_memory(self, user_id: str, query: str, top_k: int = 5) -> str:
        """Semantic search over a user's memories — returns relevant snippets."""
        if self.client is None:
            return ""
        try:
            result = await self.client.search(query, filters={"user_id": user_id}, top_k=top_k)
            memories = result if isinstance(result, list) else result.get("results", [])
            return "\n".join(m["memory"] for m in memories if m.get("memory"))
        except Exception as e:
            logger.warning("Mem0 search failed: %s", e)
            return ""

    async def delete_user_memory(self, user_id: str) -> None:
        """Delete all memories for a user."""
        if self.client is None:
            return
        try:
            await self.client.delete_all(user_id=user_id)
        except Exception as e:
            logger.warning("Mem0 delete failed: %s", e)
