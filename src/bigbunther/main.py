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
SNAPSHOT_URL = env.str("SNAPSHOT_URL", None)
SNAPSHOT_FILENAME = env.str("SNAPSHOT_FILENAME", "creep.jpg")
STREAM_URL = env.str("STREAM_URL", None)
GIF_LENGTH = env.int("GIF_LENGTH", 5)
GIF_FPS = env.int("GIF_FPS", 15)
DISCORD_TOKEN = env.str("DISCORD_TOKEN")


# Job locks
SNAPSHOT_LOCK = asyncio.Lock()
GIF_LOCK = asyncio.Lock()


# Discord Bot Setup
BOT = commands.Bot(
    command_prefix="!",
    intents=discord.Intents.default(),
    activity=discord.Activity(
        name="two little idiots", type=discord.ActivityType.watching
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


@BOT.tree.command(name="creep", description="Creep on the buns")
async def creep_on_buns(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    if not SNAPSHOT_URL:
        await interaction.followup.send("No snapshot URL provided.")
        await log.aerror("No snapshot URL provided")
        return

    if SNAPSHOT_LOCK.locked():
        await interaction.followup.send(
            "Already creeping on the buns. Please wait or try again later."
        )
        await log.awarning("Already creeping on the buns")
        return

    async with SNAPSHOT_LOCK:
        await log.ainfo("Creeping on the buns", user=interaction.user.name)
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
        await log.ainfo("Creeped on the buns")


@BOT.tree.command(
    name="linger",
    description="Creep on the buns (but linger long enough to make a gif)",
)
async def linger_on_buns(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    if not STREAM_URL:
        await interaction.followup.send("No stream URL provided.")
        await log.aerror("No stream URL provided")
        return

    if GIF_LOCK.locked():
        await interaction.followup.send(
            "Already lingering on the buns. Please wait or try again later."
        )
        await log.warning("Already lingering on the buns")
        return

    async with GIF_LOCK:
        await log.ainfo("Lingering on the buns", user=interaction.user.name)
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
        await log.ainfo("Lingered on the buns")


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
        result = await ffmpeg.execute(timeout=30)
    except asyncio.TimeoutError as e:
        await log.aerror("Timed out while fetching gif", stdout=result)
        raise e


if __name__ == "__main__":
    asyncio.run(start_bot())
