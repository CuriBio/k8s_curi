from fastapi import FastAPI, APIRouter
from databases import Database
from lib.models import *
from endpoints import segmentations
from endpoints import segtrainings
from endpoints import trainings
from endpoints import classifications
from endpoints import dashboard
from endpoints import user

# DATABASE_URL = os.enviorn.get('DATABASE_URL')
DATABASE_URL = "postgresql://luci@localhost/pheno_test"
db = Database(DATABASE_URL)

app = FastAPI()
api_router = APIRouter()

api_router.include_router(user.router)
api_router.include_router(dashboard.router)
api_router.include_router(segmentations.router)
api_router.include_router(segtrainings.router)
api_router.include_router(trainings.router)
api_router.include_router(classifications.router)

app.include_router(api_router)


@app.on_event("startup")
async def startup():
    await db.connect()


@app.on_event("shutdown")
async def shutdown():
    await db.disconnect()
