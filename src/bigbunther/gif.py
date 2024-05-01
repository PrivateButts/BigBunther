import asyncio
import io
from pathlib import Path
import time
import environ
import structlog
from ffmpeg.asyncio import FFmpeg
from ffmpeg import Progress
from pygifsicle import optimize


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
    output_name = f"test_{int(time.time())}.gif"
    ffmpeg = (
        FFmpeg()
        .option("y")
        .option("t", GIF_LENGTH)
        .option("r", 15)
        .input(
            STREAM_URL,
            rtsp_transport="tcp",
            rtsp_flags="prefer_tcp",
        )
        .output(
            output_name,
            r=15,
            t=GIF_LENGTH,
            filter_complex="[0:v] split [a][b];[a] palettegen [p];[b][p] paletteuse",
        )
    )

    @ffmpeg.on("progress")
    def on_progress(progress: Progress):
        print(progress)

    log.info("Starting FFMPEG", args=ffmpeg.arguments)
    try:
        result = await ffmpeg.execute(timeout=30 * 4)
    except asyncio.TimeoutError:
        log.error("Timed out while fetching gif", stdout=ffmpeg)
        return None

    log.info(
        "Gif fetched, optimizing",
        stdout=result,
    )

    # Optimize the gif
    gif_path = Path(output_name)
    optimized_path = gif_path.with_name(f"{gif_path.stem}_optimized.gif")
    optimize(gif_path, optimized_path, options=["--lossy=100"])
    log.info("Gif optimized", path=optimized_path)


if __name__ == "__main__":
    asyncio.run(get_gif())
