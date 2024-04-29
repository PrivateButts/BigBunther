import asyncio
import io
from pathlib import Path
import environ
import aiohttp
import structlog
from ffmpeg.asyncio import FFmpeg
from ffmpeg import Progress
import discord
from discord.ext import commands


# Basics
env = environ.Env()
log = structlog.get_logger()


# Set the project base directory
BASE_DIR = Path(__file__).resolve().parent

# Take environment variables from .env file
environ.Env.read_env(BASE_DIR / ".env")


# Environment Variables
SNAPSHOT_URL = env.str("SNAPSHOT_URL", None)
SNAPSHOT_FILENAME = env.str("SNAPSHOT_FILENAME", "creep.jpg")
STREAM_URL = env.str("STREAM_URL", None)
GIF_LENGTH = env.int("GIF_LENGTH", 5)
DISCORD_TOKEN = env.str("DISCORD_TOKEN")


async def get_gif():
    """Fetches a gif from stream_url. Returns a BytesIO."""
    ffmpeg = (
        FFmpeg()
        .option("y")
        .input(
            STREAM_URL,
            rtsp_transport="tcp",
            rtsp_flags="prefer_tcp",
        )
        .output("test.gif", vf="fps=15", t=GIF_LENGTH)
    )

    try:
        result = await ffmpeg.execute(timeout=30)
    except asyncio.TimeoutError:
        log.error("Timed out while fetching gif", stdout=result)
        return None
    log.info("Gif fetched", stdout=result)


if __name__ == "__main__":
    asyncio.run(get_gif())
