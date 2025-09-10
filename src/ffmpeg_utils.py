import ffmpeg
import os

def convert_to_gif(input_path, output_path):
    """
    Convert MP4 to GIF and optimize for size.
    Target: under 8MB if possible.
    """
    try:
        (
            ffmpeg
            .input(input_path)
            .output(output_path,
                    vf='scale=480:-1:flags=lanczos,fps=15',
                    loop=0)
            .overwrite_output()
            .run(quiet=True)
        )
        return output_path
    except ffmpeg.Error as e:
        print("FFmpeg error:", e)
        return None

def get_filesize_mb(filepath):
    size = os.path.getsize(filepath) / (1024 * 1024)
    return round(size, 2)
