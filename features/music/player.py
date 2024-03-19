from asyncio import Queue, TimeoutError
from contextlib import suppress

import async_timeout
from discord import HTTPException, Message, TextChannel
from pomice import Player, Track


class Player(Player):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bound_channel: TextChannel = None
        self.message: Message = None
        self.track: Track = None
        self.queue: Queue = Queue()
        self.waiting: bool = False
        self.loop: str = False

    async def play(self, track: Track):
        await super().play(track)

    async def insert(self, track: Track, filter: bool = True, bump: bool = False):
        if filter and track.info.get("sourceName", "Spotify") == "youtube":
            response = await self.bot.session.get(
                "https://metadata-filter.vercel.app/api/youtube",
                params=dict(track=track.title),
            )
            data = await response.json()

            if data.get("status") == "success":
                track.title = data["data"].get("track")

        if bump:
            queue = self.queue._queue
            queue.insert(0, track)
        else:
            await self.queue.put(track)

        return True

    async def next_track(self, ignore_playing: bool = False):
        if not ignore_playing and self.is_playing or self.waiting:
            return

        self.waiting = True
        if self.loop == "track" and self.track:
            track = self.track
        else:
            try:
                with async_timeout.timeout(300):
                    track = await self.queue.get()
                    if self.loop == "queue":
                        await self.queue.put(track)
            except TimeoutError:
                return await self.teardown()

        await self.play(track)
        self.track = track
        self.waiting = False
        if self.bound_channel and self.loop != "track":
            try:
                if self.message:
                    async for message in self.bound_channel.history(limit=15):
                        if message.id == self.message.id:
                            with suppress(HTTPException):
                                await message.delete()
                            break

                self.message = await track.ctx.neutral(
                    f"Now playing [**{track.title}**]({track.uri})"
                )
            except:  # noqa
                self.bound_channel = None

        return track

    async def skip(self):
        if self.is_paused:
            await self.set_pause(False)

        return await self.stop()

    async def set_loop(self, state: str):
        self.loop = state

    async def teardown(self):
        with suppress(Exception):
            self.queue._queue.clear()
            await self.reset_filters()
            await self.destroy()

    def __repr__(self):
        return f"<Player guild={self.guild.id} connected={self.is_connected} playing={self.is_playing}>"
