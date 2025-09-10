import os
import subprocess

MAX_GIF_SIZE_MB = 8

async def convert_to_gif(input_path):
    """
    Converts a video/image/GIF to GIF format and compresses if needed.
    Ensures the output is <= 8MB for Telegram.
    """
    base_output = input_path.rsplit(".", 1)[0]
    output_path = f"{base_output}.gif"

    # Initial conversion
    await _run_ffmpeg_convert(input_path, output_path)

    # Check size and compress if needed
    size_mb = get_filesize_mb(output_path)
    if size_mb > MAX_GIF_SIZE_MB:
        output_path = await compress_gif(output_path)

    return output_path

async def _run_ffmpeg_convert(input_path, output_path):
    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-vf", "fps=15,scale=480:-1:flags=lanczos",
        "-pix_fmt", "rgb24",
        output_path
    ]
    process = subprocess.run(cmd, capture_output=True)
    if process.returncode != 0:
        raise RuntimeError(process.stderr.decode())

async def compress_gif(input_path):
    """
    Iteratively compresses the GIF until it's <= 8MB.
    Reduces frame rate and width progressively.
    """
    current_path = input_path
    size_mb = get_filesize_mb(current_path)
    fps = 15
    width = 480

    while size_mb > MAX_GIF_SIZE_MB:
        fps = max(5, fps - 2)
        width = max(200, width - 50)
        compressed_path = current_path.rsplit(".", 1)[0] + f"_compressed.gif"

        cmd = [
            "ffmpeg", "-y",
            "-i", current_path,
            "-vf", f"fps={fps},scale={width}:-1:flags=lanczos",
            "-pix_fmt", "rgb24",
            compressed_path
        ]
        process = subprocess.run(cmd, capture_output=True)
        if process.returncode != 0:
            raise RuntimeError(process.stderr.decode())

        current_path = compressed_path
        size_mb = get_filesize_mb(current_path)

        if fps <= 5 and width <= 200:
            # Bail out if it's still too big at extreme compression
            break

    return current_path

def get_filesize_mb(path):
    return os.path.getsize(path) / (1024 * 1024)
