from langchain_anthropic import ChatAnthropic
from typing import Optional, Dict, Any, List, Union
from langchain_core.messages import BaseMessage, SystemMessage
import os

class CachedChatAnthropic(ChatAnthropic):
    """Extended ChatAnthropic with Claude API prompt caching support"""

    # Define additional fields for Pydantic
    enable_caching: bool = True
    cache_ttl: str = "1h"
    min_cache_tokens: int = 1024

    def __init__(
        self,
        model_name: str = "claude-sonnet-4-20250514",
        max_tokens: int = 64000,
        enable_caching: bool = True,
        cache_ttl: str = "1h",  # "5m" or "1h"
        min_cache_tokens: int = 1024,
        **kwargs
    ):
        super().__init__(
            model_name=model_name,
            max_tokens=max_tokens,
            enable_caching=enable_caching,
            cache_ttl=cache_ttl,
            min_cache_tokens=min_cache_tokens,
            **kwargs
        )

    def _add_cache_control_to_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Add cache control markers to the API payload before sending"""
        if not self.enable_caching:
            return payload

        # Check if there's a system message to cache
        if 'system' in payload and payload['system']:
            system = payload['system']

            # If system is a string and large enough, convert to list format with cache control
            if isinstance(system, str) and len(system) >= self.min_cache_tokens * 4:
                payload['system'] = [{
                    "type": "text",
                    "text": system,
                    "cache_control": {
                        "type": "ephemeral",
                        "ttl": self.cache_ttl
                    }
                }]
                print(f"🔄 Added cache control to system message (~{len(system)//4} tokens)")

            # If system is already a list, add cache control to large text blocks
            elif isinstance(system, list):
                for block in system:
                    if (isinstance(block, dict) and
                        block.get("type") == "text" and
                        len(block.get("text", "")) >= self.min_cache_tokens * 4):

                        if "cache_control" not in block:
                            block["cache_control"] = {
                                "type": "ephemeral",
                                "ttl": self.cache_ttl
                            }
                            print(f"🔄 Added cache control to system block (~{len(block['text'])//4} tokens)")

        return payload

    def _create(self, payload: Dict[str, Any], **kwargs) -> Any:
        """Override _create to add cache control before API call"""
        # Add cache control to payload
        cached_payload = self._add_cache_control_to_payload(payload.copy())

        # Call parent method with modified payload
        return super()._create(cached_payload, **kwargs)

    async def _acreate(self, payload: Dict[str, Any], **kwargs) -> Any:
        """Override _acreate to add cache control before async API call"""
        # Add cache control to payload
        cached_payload = self._add_cache_control_to_payload(payload.copy())

        # Call parent method with modified payload
        return await super()._acreate(cached_payload, **kwargs)

    def _log_cache_info(self, content_length: int, cached: bool = False):
        """Log caching information for debugging"""
        if self.enable_caching:
            status = "CACHED" if cached else "CACHE_ELIGIBLE"
            print(f"🔄 Cache {status}: ~{content_length // 4} tokens (~{content_length} chars)")

def get_cached_model(
    model_name: Optional[str] = None,
    enable_caching: bool = True,
    cache_ttl: str = "1h",
    min_cache_tokens: int = 1024
) -> CachedChatAnthropic:
    """
    Factory function for cached Claude model instances.

    Args:
        model_name: Claude model to use
        enable_caching: Enable prompt caching
        cache_ttl: Cache duration ("5m" or "1h")
        min_cache_tokens: Minimum tokens required for caching

    Returns:
        CachedChatAnthropic instance with caching support
    """
    return CachedChatAnthropic(
        model_name=model_name or "claude-sonnet-4-20250514",
        max_tokens=64000,
        enable_caching=enable_caching,
        cache_ttl=cache_ttl,
        min_cache_tokens=min_cache_tokens
    )