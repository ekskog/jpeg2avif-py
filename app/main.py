from fastapi import FastAPI, UploadFile, File, HTTPException
from app.converter import convert_jpeg_to_avif_variants
import base64
import gc
import psutil
import os

app = FastAPI()

def get_memory_info():
    """Get current memory usage information"""
    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()
    return {
        "rss_mb": round(memory_info.rss / 1024 / 1024, 2),  # Resident Set Size
        "vms_mb": round(memory_info.vms / 1024 / 1024, 2),  # Virtual Memory Size
        "percent": round(process.memory_percent(), 2)
    }

@app.get("/health")
async def health_check():
    memory = get_memory_info()
    
    # Only log health check if there's an issue
    if memory["percent"] > 80:
        print(f"[HEALTH] Service status check - Memory: {memory['percent']}%")
    
    return {
        "status": "healthy", 
        "service": "jpg2avif-py",
        "memory": memory
    }

@app.post("/convert")
async def convert_image(image: UploadFile = File(...)):
    # Log initial memory state
    memory_before = get_memory_info()
    jpeg_size_mb = 0
    
    print(f"[CONVERT] Starting conversion - Memory before: RSS={memory_before['rss_mb']}MB, VMS={memory_before['vms_mb']}MB, {memory_before['percent']}%")
    
    if image.content_type != "image/jpeg":
        raise HTTPException(status_code=400, detail="Only JPEG images are supported.")
    
    jpeg_data = await image.read()
    jpeg_size_mb = round(len(jpeg_data) / 1024 / 1024, 2)
    
    print(f"[CONVERT] Processing {image.filename or 'unknown'}: JPEG input size = {jpeg_size_mb}MB")
    
    # Initialize fullsize_data to None
    fullsize_data = None
    
    try:
        # Check memory after reading file
        memory_after_read = get_memory_info()
        print(f"[CONVERT] Memory after reading JPEG: RSS={memory_after_read['rss_mb']}MB (+{memory_after_read['rss_mb'] - memory_before['rss_mb']}MB)")
        
        # Convert to AVIF (full-size only) using the original filename
        fullsize_data = convert_jpeg_to_avif_variants(jpeg_data, image.filename or "image.jpg")
        avif_size_mb = round(len(fullsize_data) / 1024 / 1024, 2)
        compression_ratio = round((1 - len(fullsize_data) / len(jpeg_data)) * 100, 1)
        
        print(f"[CONVERT] Conversion complete: AVIF output size = {avif_size_mb}MB ({compression_ratio}% compression)")
        
        # Check memory after conversion
        memory_after_conversion = get_memory_info()
        print(f"[CONVERT] Memory after conversion: RSS={memory_after_conversion['rss_mb']}MB (+{memory_after_conversion['rss_mb'] - memory_before['rss_mb']}MB from start)")
        
        # Encode to base64 in chunks to avoid keeping multiple copies in memory
        fullsize_b64 = base64.b64encode(fullsize_data).decode('utf-8')
        
        # Check memory after base64 encoding
        memory_after_b64 = get_memory_info()
        print(f"[CONVERT] Memory after base64 encoding: RSS={memory_after_b64['rss_mb']}MB (+{memory_after_b64['rss_mb'] - memory_before['rss_mb']}MB from start)")
        
        # Store the size before cleanup
        output_size = len(base64.b64decode(fullsize_b64))
        
        # Cleanup variables to free memory - be more aggressive
        del jpeg_data  # Remove input data
        if fullsize_data is not None:
            del fullsize_data  # Remove AVIF binary data
        
        # Force multiple garbage collection passes
        for _ in range(3):
            gc.collect()
        
        # Check memory after aggressive cleanup
        memory_after_cleanup = get_memory_info()
        memory_freed = memory_after_b64['rss_mb'] - memory_after_cleanup['rss_mb']
        print(f"[CONVERT] Memory after aggressive cleanup: RSS={memory_after_cleanup['rss_mb']}MB (freed {memory_freed}MB)")
        
        # If still no memory freed, log warning
        if memory_freed < 1.0 and jpeg_size_mb > 5.0:  # Only warn for larger files
            print(f"[CONVERT] WARNING: Expected to free ~{jpeg_size_mb}MB but only freed {memory_freed}MB - potential memory leak")
        
        return {
            "success": True,
            "fullSize": {
                "data": fullsize_b64,
                "size": output_size
            },
            "stats": {
                "input_size_mb": jpeg_size_mb,
                "output_size_mb": avif_size_mb,
                "compression_ratio": compression_ratio,
                "memory_peak_mb": memory_after_b64['rss_mb'],
                "memory_freed_mb": memory_freed,
                "memory_final_mb": memory_after_cleanup['rss_mb']
            }
        }
    except Exception as e:
        # Clean up and log memory state on error
        gc.collect()
        memory_after_error = get_memory_info()
        print(f"[CONVERT] Error occurred: {str(e)}")
        print(f"[CONVERT] Memory after error cleanup: RSS={memory_after_error['rss_mb']}MB")

        return {
            "success": False,
            "error": str(e)
        }