from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import Response
from app.converter import convert_jpeg_to_avif

app = FastAPI()

@app.post("/convert")
async def convert_image(file: UploadFile = File(...)):
    if file.content_type != "image/jpeg":
        raise HTTPException(status_code=400, detail="Only JPEG images are supported.")
    
    jpeg_data = await file.read()
    try:
        avif_data = convert_jpeg_to_avif(jpeg_data)
        return Response(avif_data, media_type="image/avif")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
