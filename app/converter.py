import subprocess
import tempfile
from pathlib import Path

def convert_jpeg_to_avif(jpeg_data: bytes) -> bytes:
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = Path(tmpdir) / "input.jpg"
        output_path = Path(tmpdir) / "output.avif"
        input_path.write_bytes(jpeg_data)

        result = subprocess.run([
            "avifenc", str(input_path), str(output_path)
        ], capture_output=True)

        if result.returncode != 0:
            raise RuntimeError(f"Conversion failed: {result.stderr.decode()}")

        return output_path.read_bytes()
