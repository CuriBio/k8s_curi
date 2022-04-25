from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI(docs_url=None, redoc_url=None)


@app.get("/")
async def root():
    return JSONResponse({"message": "test"})
