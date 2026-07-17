import os
from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI()


@app.get("/")
async def root():
    return {"status": "ok", "message": "AskMyPDF service is running."}


@app.get("/health")
async def health():
    return JSONResponse({"status": "healthy"})


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app:app", host="0.0.0.0", port=port)
