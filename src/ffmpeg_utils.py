import ffmpeg
import os

MAX_FILESIZE_MB = 8

def convert_to_gif(input_path, output_path):
    """
    Convert MP4 to GIF and compress until under 8MB if possible.
    """
    try:
        # First pass: normal settings (480p, 15fps, full color)
        _convert(input_path, output_path, scale=480, fps=15, colors=256)

        if get_filesize_mb(output_path) <= MAX_FILESIZE_MB:
            return output_path

        # Second pass: reduce resolution
        _convert(input_path, output_path, scale=360, fps=15, colors=256)
        if get_filesize_mb(output_path) <= MAX_FILESIZE_MB:
            return output_path

        # Third pass: reduce FPS
        _convert(input_path, output_path, scale=360, fps=10, colors=256)
        if get_filesize_mb(output_path) <= MAX_FILESIZE_MB:
            return output_path

        # Final pass: reduce colors
        _convert(input_path, output_path, scale=320, fps=10, colors=128)
        return output_path

    except ffmpeg.Error as e:
        print("FFmpeg error:", e)
        return None


def _convert(input_path, output_path, scale=480, fps=15, colors=256):
    """
    Helper: perform actual ffmpeg conversion with palette optimization.
    """
    palette = f"{output_path}.png"

    # Step 1: Generate palette for optimal colors
    ffmpeg.input(input_path).output(
        palette,
        vf=f"fps={fps},scale={scale}:-1:flags=lanczos,palettegen=max_colors={colors}"
    ).overwrite_output().run(quiet=True)

    # Step 2: Apply palette to final GIF
    ffmpeg.input(input_path).filter(
        "fps", fps
    ).filter(
        "scale", scale, -1, flags="lanczos"
    ).filter_complex(
        f"[0:v][1:v]paletteuse"
    ).input(palette).output(
        output_path, loop=0
    ).overwrite_output().run(quiet=True)

    os.remove(palette)  # Clean up temp palette


def get_filesize_mb(filepath):
    size = os.path.getsize(filepath) / (1024 * 1024)
    return round(size, 2)
