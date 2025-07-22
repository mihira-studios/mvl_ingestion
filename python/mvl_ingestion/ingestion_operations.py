import os
import shutil
import subprocess
from mvl_ingestion.ingestion_utils import logger
# import logging
# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s %(levelname)s [%(filename)s:%(lineno)d] %(message)s'
# )

class FileOperation:
    """Base class for file operations."""
    def execute(self, *args, **kwargs):
        raise NotImplementedError

class CopyFileOperation(FileOperation):
    def execute(self, src, dst, overwrite=False):
        if os.path.exists(dst) and os.path.getsize(dst) > 0 and os.path.getsize(src) > 0 and not overwrite:
            logger.info(f"Skipped copy (already exists): {os.path.basename(dst)}")
            return
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)

        # Validate file sizes
        src_size = os.path.getsize(src)
        dst_size = os.path.getsize(dst)
        if src_size == dst_size:
            logger.info(f"Copied file: {os.path.basename(src)} to {dst} (size validated)")
        else:
            logger.warning(f"Size mismatch for {src} -> {dst}: src={src_size}, dst={dst_size}")
        

class ProxyGenerationOperation(FileOperation):
    def execute(self, input_path, output_path, resolution):
        command = [
            "oiiotool",
            str(input_path),
            "--resize", resolution,
            "-o", str(output_path)
        ]
        try:
            subprocess.run(command, check=True, capture_output=True)
        except Exception as e:
            logger.info(f"Proxy generation failed: {e}")

class MovGenerationOperation(FileOperation):
    def execute(self, input_pattern, output_mov, metadata, fps=24):
        try:
            from mvl_make_dailies.movie_commands import create_movie_from_sequence

            data = {
                'input': input_pattern,
                'output': output_mov,
                'topleft' :  metadata.get('vendor'),
                'topcenter': os.path.basename(input_pattern).split('_')[0], # show code
                'bottomleft': os.path.basename(input_pattern).split('_')[-1] # version
            }
            create_movie_from_sequence(data)
        except Exception as e:
            logger.warning(f"mvl_make_dailies failed: {e}")
            logger.info("Falling back to ffmpeg...")
            ffmpeg_cmd = [
                "ffmpeg",
                "-framerate", "24",
                "-i", input_pattern,
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-y",  # Overwrite output
                output_mov
            ]
            try:
                subprocess.run(ffmpeg_cmd, check=True)
                logger.info(f"Successfully generated MOV using ffmpeg: {output_mov}")
            except subprocess.CalledProcessError as ffmpeg_error:
                logger.error(f"ffmpeg failed to generate movie: {ffmpeg_error}")