import subprocess
import tempfile
from pathlib import Path
from typing import Tuple
import psutil
import os
import gc

def get_memory_usage():
    """Get current memory usage in MB"""
    process = psutil.Process(os.getpid())
    return round(process.memory_info().rss / 1024 / 1024, 2)

def convert_jpeg_to_avif_variants(jpeg_data: bytes, original_filename: str = "image.jpg") -> bytes:
    """
    Convert JPEG to AVIF (full-size only)
    Returns AVIF data as bytes
    """
    memory_start = get_memory_usage()
    print(f"[CONVERTER] Starting conversion of {original_filename} - Memory: {memory_start}MB")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = Path(tmpdir) / "input.jpg"
        
        # Use original filename for output, just change extension to .avif
        base_name = Path(original_filename).stem  # Gets filename without extension
        output_path = Path(tmpdir) / f"{base_name}.avif"
        
        # Write input JPEG
        input_path.write_bytes(jpeg_data)
        memory_after_write = get_memory_usage()
        print(f"[CONVERTER] JPEG written to temp file - Memory: {memory_after_write}MB (+{memory_after_write - memory_start}MB)")

        # Convert to AVIF - optimized for quality
        print(f"[CONVERTER] Starting avifenc conversion...")
        result = subprocess.run([
            "avifenc", 
            "--min", "0", "--max", "18",  # High quality (0=best, 18≈90% JPEG quality)
            "--speed", "10",  # Maximum speed (0=slowest/best, 10=fastest)
            "--jobs", "4",  # Use 4 threads for faster encoding
            str(input_path), 
            str(output_path)
        ], capture_output=True)

        memory_after_conversion = get_memory_usage()
        print(f"[CONVERTER] avifenc completed - Memory: {memory_after_conversion}MB (+{memory_after_conversion - memory_start}MB from start)")

        if result.returncode != 0:
            print(f"[CONVERTER] avifenc failed with error: {result.stderr.decode()}")
            raise RuntimeError(f"AVIF conversion failed: {result.stderr.decode()}")

        # Read the converted file
        avif_data = output_path.read_bytes()
        memory_after_read = get_memory_usage()
        
        input_size_mb = round(len(jpeg_data) / 1024 / 1024, 2)
        output_size_mb = round(len(avif_data) / 1024 / 1024, 2)
        compression_ratio = round((1 - len(avif_data) / len(jpeg_data)) * 100, 1)
        
        print(f"[CONVERTER] Conversion successful: {input_size_mb}MB → {output_size_mb}MB ({compression_ratio}% compression)")
        print(f"[CONVERTER] AVIF data read - Memory: {memory_after_read}MB (+{memory_after_read - memory_start}MB from start)")
        
        # Force cleanup before returning
        del jpeg_data  # Remove reference to input data
        gc.collect()
        
        memory_final = get_memory_usage()
        print(f"[CONVERTER] Cleanup complete - Final memory: {memory_final}MB")
        
        return avif_data
