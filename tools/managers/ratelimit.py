from typing import Any

from discord.ext.commands import CooldownMapping

mappings: dict[str, CooldownMapping] = {}


def handle_bucket(key: Any) -> Any:
    """A function that returns the key for the ratelimit."""
    return key


def ratelimiter(
    bucket: str,
    key: Any,
    rate: int,
    per: float,
) -> int | None:
    """A method that handles cooldown buckets"""
    if not (mapping := mappings.get(bucket)):
        mapping = mappings[bucket] = CooldownMapping.from_cooldown(
            rate, per, handle_bucket
        )

    bucket = mapping.get_bucket(key)
    return bucket.update_rate_limit()
