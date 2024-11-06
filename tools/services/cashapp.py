# broken? idk

import re
import sys
from datetime import timedelta
from os import path

from orjson import loads
from yarl import URL

from tools.managers import ClientSession, cache
from tools.models import CashApp, CashAppAvatar

script_dir = path.dirname(path.abspath(__file__))
sys.path.append(script_dir)


@cache(ttl=timedelta(minutes=60), key="{username}")
async def profile(session: ClientSession, username: str) -> CashApp:
    data = await session.request(
        "GET",
        URL("https://cash.app/$" + username.replace("$", "")),
        raise_for={
            404: f"Profile [**{username}**](https://cash.app/{URL(username.replace('$', ''))}) not found"
        },
    )

    match = re.search(r"var profile = (\{.*?\});", str(data))
    profile_json = match[1]
    profile_data = loads(profile_json)
    avatar = profile_data.get("avatar", {})

    return CashApp(
        url=f"https://cash.app/${URL(username.replace('$', ''))}",
        cashtag=profile_data.get("formatted_cashtag"),
        display_name=profile_data.get("display_name"),
        country_code=profile_data.get("country_code"),
        avatar_url=CashAppAvatar(
            image_url=avatar.get("image_url"),
            accent_color=avatar.get("accent_color"),
        ),
        qr=f"https://cash.app/qr/{profile_data.get('formatted_cashtag')}",
    )
