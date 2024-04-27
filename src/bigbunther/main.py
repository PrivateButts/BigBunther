import asyncio
import io
from pathlib import Path
import environ
import aiohttp
import structlog
from PIL import Image
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
SNAPSHOT_URL = env.str("SNAPSHOT_URL")
DISCORD_TOKEN = env.str("DISCORD_TOKEN")


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
    await log.ainfo("Creeping on the buns", user=interaction.user.name)
    try:
        image = await get_snapshot()
    except Exception as e:
        await interaction.followup.send(
            "Failed to fetch image. Please try again later."
        )
        await log.error("Failed to fetch image", error=str(e))
        return
    image_buffer = io.BytesIO()
    image.save(image_buffer, format="PNG")
    image_buffer.seek(0)
    await interaction.followup.send(
        content="👀", file=discord.File(image_buffer, "creep.png")
    )
    await log.ainfo("Creeped on the buns")


async def get_snapshot() -> Image:
    """Fetches an image from self.url. Returns a PIL Image."""
    async with aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=env.int("HTTP_TIMEOUT", 30))
    ) as session:
        async with session.get(SNAPSHOT_URL) as resp:
            if resp.status != 200:
                raise Exception(f"Failed to fetch image: {resp.status} {resp.reason}")
            await log.adebug("Fetched image", url=SNAPSHOT_URL, status=resp.status)
            return Image.open(io.BytesIO(await resp.read()))


if __name__ == "__main__":
    asyncio.run(start_bot())
