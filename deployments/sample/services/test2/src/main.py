from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI(openapi_url=None)


@app.get("/")
async def root():
    return JSONResponse({"message": "test"})
