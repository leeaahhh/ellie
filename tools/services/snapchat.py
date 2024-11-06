# not implemented and probably never will be

from datetime import timedelta

from orjson import loads

from tools.managers import ClientSession, cache
from tools.models import SnapchatHighlight, SnapchatProfile


@cache(ttl=timedelta(minutes=60), key="{username}")
async def profile(
    session: ClientSession,
    username: str,
) -> SnapchatProfile:
    data = await session.request(
        "GET",
        f"https://story.snapchat.com/add/{username}",
        raise_for={
            404: f"Profile [**{username}**](https://story.snapchat.com/add/{username}) not found"
        },
    )

    props = loads(data.find("script", {"id": "__NEXT_DATA__"}).text)["props"][
        "pageProps"
    ]
    data = props["userProfile"].get("publicProfileInfo") or props["userProfile"].get(
        "userInfo"
    )

    return SnapchatProfile(
        url=f"https://story.snapchat.com/add/{username}",
        username=username,
        display_name=(data.get("displayName") or data.get("title") or username),
        description=data.get("bio"),
        snapcode=(data["snapcodeImageUrl"].replace("SVG", "PNG")),
        bitmoji=(
            (bitmoji.get("avatarImage").get("url"))
            if (bitmoji := data.get("bitmoji3d"))
            else None
        ),
        subscribers=int(data.get("subscriberCount", 0)),
        stories=[
            SnapchatHighlight(
                type="image" if story["snapMediaType"] == 0 else "video",
                url=story["snapUrls"]["mediaUrl"],
            )
            for story in props.get("story", {}).get("snapList", [])
        ],
        highlights=(
            [
                SnapchatHighlight(
                    type="image" if highlight["snapMediaType"] == 0 else "video",
                    url=highlight["snapUrls"]["mediaUrl"],
                )
                for highlight in highlights[0].get("snapList", [])
            ]
            if (highlights := props.get("spotlightHighlights", []))
            else []
        ),
    )
