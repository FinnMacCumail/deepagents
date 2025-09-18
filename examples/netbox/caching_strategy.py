"""
Advanced caching strategies for NetBox agent optimization
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import hashlib
import json

@dataclass
class CacheStrategy:
    """Define caching strategy based on query patterns"""

    # Query type classifications
    SIMPLE_QUERIES = ["list", "show", "get", "check"]  # 5-min cache
    COMPLEX_QUERIES = ["audit", "report", "analyze", "trace"]  # 1-hour cache
    INTERACTIVE_QUERIES = ["explore", "investigate", "debug"]  # 1-hour cache

    @classmethod
    def determine_cache_ttl(cls, query: str) -> str:
        """Determine optimal cache TTL based on query type"""
        query_lower = query.lower()

        # Check for complex/long-running query patterns
        for keyword in cls.COMPLEX_QUERIES:
            if keyword in query_lower:
                return "1h"

        # Check for interactive exploration patterns
        for keyword in cls.INTERACTIVE_QUERIES:
            if keyword in query_lower:
                return "1h"

        # Default to short cache for simple queries
        return "default"

    @classmethod
    def should_cache_conversation(cls, messages: List[Dict], threshold: int = 3) -> bool:
        """Determine if conversation history should be cached"""
        # Cache if conversation has more than threshold turns
        user_messages = [m for m in messages if m.get("role") == "user"]
        return len(user_messages) > threshold

    @classmethod
    def generate_cache_key(cls, content: str) -> str:
        """Generate a cache key for content deduplication"""
        return hashlib.md5(content.encode()).hexdigest()[:8]

class DynamicCacheManager:
    """Manage dynamic caching decisions based on usage patterns"""

    def __init__(self):
        self.query_history = []
        self.cache_keys = {}
        self.session_start = None

    def optimize_caching(self, query: str, session_duration: float) -> Dict[str, Any]:
        """Determine optimal caching parameters for current query"""

        # Determine cache TTL based on query type
        cache_ttl = CacheStrategy.determine_cache_ttl(query)

        # Use longer cache for extended sessions (> 5 minutes)
        if session_duration > 300:
            cache_ttl = "1h"

        # Check if this is a repeated query pattern
        query_key = CacheStrategy.generate_cache_key(query)
        is_repeated = query_key in self.cache_keys

        return {
            "enable_caching": True,
            "cache_ttl": cache_ttl,
            "cache_conversation": session_duration > 180,  # Cache after 3 minutes
            "is_repeated_pattern": is_repeated,
            "optimization_reason": self._get_optimization_reason(query, session_duration, is_repeated)
        }

    def _get_optimization_reason(self, query: str, session_duration: float, is_repeated: bool) -> str:
        """Explain caching decision"""
        reasons = []

        if "report" in query.lower() or "audit" in query.lower():
            reasons.append("Complex query detected - using 1-hour cache")
        elif session_duration > 300:
            reasons.append("Extended session - using 1-hour cache")
        elif is_repeated:
            reasons.append("Repeated query pattern - maximizing cache reuse")
        else:
            reasons.append("Standard query - using 5-minute cache")

        return " | ".join(reasons)

# Example usage in netbox_agent.py
cache_manager = DynamicCacheManager()

def create_optimized_netbox_agent(session_context: Optional[Dict] = None):
    """Create NetBox agent with optimized caching based on context"""
    from netbox_agent import create_netbox_agent_with_all_tools

    # Analyze session context
    if session_context:
        query = session_context.get("initial_query", "")
        session_duration = session_context.get("duration", 0)

        # Get optimized cache settings
        cache_config = cache_manager.optimize_caching(query, session_duration)

        print(f"🧠 Cache Optimization: {cache_config['optimization_reason']}")

        return create_netbox_agent_with_all_tools(
            enable_caching=cache_config["enable_caching"],
            cache_ttl=cache_config["cache_ttl"],
            cache_conversation=cache_config["cache_conversation"]
        )

    # Default configuration
    return create_netbox_agent_with_all_tools()