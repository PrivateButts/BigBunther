import asyncio
import io
from pathlib import Path
import environ
import aiohttp
import structlog
from ffmpeg.asyncio import FFmpeg
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
TARGET_NAME = env.str("TARGET_NAME", "buns")
SNAPSHOT_URL = env.str("SNAPSHOT_URL", None)
SNAPSHOT_FILENAME = env.str("SNAPSHOT_FILENAME", "creep.jpg")
STREAM_URL = env.str("STREAM_URL", None)
GIF_LENGTH = env.int("GIF_LENGTH", 5)
GIF_FPS = env.int("GIF_FPS", 15)
DISCORD_TOKEN = env.str("DISCORD_TOKEN")
DISCORD_COMMAND_PREFIX = env.str("DISCORD_COMMAND_PREFIX", "")
DISCORD_ACTIVITY_MESSAGE = env.str("DISCORD_ACTIVITY_MESSAGE", "two little dorks")


# Job locks
SNAPSHOT_LOCK = asyncio.Lock()
GIF_LOCK = asyncio.Lock()


# Discord Bot Setup
BOT = commands.Bot(
    command_prefix="!",
    intents=discord.Intents.default(),
    activity=discord.Activity(
        name=DISCORD_ACTIVITY_MESSAGE, type=discord.ActivityType.watching
    ),
)


async def start_bot():
    return await BOT.start(DISCORD_TOKEN)


@BOT.event
async def on_ready():
    await log.ainfo(f"Logged in as {BOT.user}.")
    try:
        synced = await BOT.tree.sync()
        await log.ainfo(f"Synced {synced} commands.")
    except Exception as e:
        await log.aexception("Failed to sync commands.", exc_info=e)


@BOT.tree.command(
    name=f"{DISCORD_COMMAND_PREFIX}creep", description=f"Creep on the {TARGET_NAME}"
)
async def creep_on_critters(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    if not SNAPSHOT_URL:
        await interaction.followup.send("No snapshot URL provided.")
        await log.aerror("No snapshot URL provided")
        return

    if SNAPSHOT_LOCK.locked():
        await interaction.followup.send(
            f"Already creeping on the {TARGET_NAME}. Please wait or try again later."
        )
        await log.awarning(f"Already creeping on the {TARGET_NAME}")
        return

    async with SNAPSHOT_LOCK:
        await log.ainfo(f"Creeping on the {TARGET_NAME}", user=interaction.user.name)
        try:
            image = await get_snapshot()
        except Exception as e:
            await interaction.followup.send(
                "Failed to fetch image. Please try again later."
            )
            await log.aerror("Failed to fetch image", error=str(e))
            return
        await interaction.followup.send(
            content="👀", file=discord.File(image, SNAPSHOT_FILENAME)
        )
        await log.ainfo(f"Creeped on the {TARGET_NAME}")


@BOT.tree.command(
    name=f"{DISCORD_COMMAND_PREFIX}linger",
    description=f"Creep on the {TARGET_NAME} (but linger long enough to make a gif)",
)
async def linger_on_critters(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    if not STREAM_URL:
        await interaction.followup.send("No stream URL provided.")
        await log.aerror("No stream URL provided")
        return

    if GIF_LOCK.locked():
        await interaction.followup.send(
            f"Already lingering on the {TARGET_NAME}. Please wait or try again later."
        )
        await log.warning(f"Already lingering on the {TARGET_NAME}")
        return

    async with GIF_LOCK:
        await log.ainfo(f"Lingering on the {TARGET_NAME}", user=interaction.user.name)
        try:
            await get_gif()
        except Exception as e:
            await interaction.followup.send(
                "Failed to fetch gif. Please try again later."
            )
            await log.aerror("Failed to fetch gif", error=str(e))
            return
        await interaction.followup.send(
            content="👀", file=discord.File(Path("output.gif"))
        )
        await log.ainfo(f"Lingered on the {TARGET_NAME}")


async def get_snapshot() -> io.BytesIO:
    """Fetches an image from snapshot_url. Returns a BytesIO."""
    async with aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=env.int("HTTP_TIMEOUT", 30))
    ) as session:
        async with session.get(SNAPSHOT_URL) as resp:
            if resp.status != 200:
                raise Exception(f"Failed to fetch image: {resp.status} {resp.reason}")
            await log.adebug("Fetched image", url=SNAPSHOT_URL, status=resp.status)
            return io.BytesIO(await resp.read())


async def get_gif() -> None:
    """Fetches a gif from stream_url. File is saved as output.gif."""
    ffmpeg = (
        FFmpeg()
        .option("y")
        .input(
            STREAM_URL,
            rtsp_transport="tcp",
            rtsp_flags="prefer_tcp",
        )
        .output("output.gif", vf=f"fps={GIF_FPS}", t=GIF_LENGTH)
    )

    try:
        result = await ffmpeg.execute(timeout=env.int("FFMPEG_TIMEOUT", 30))
    except asyncio.TimeoutError as e:
        await log.aerror("Timed out while fetching gif", stdout=result)
        raise e


if __name__ == "__main__":
    asyncio.run(start_bot())
