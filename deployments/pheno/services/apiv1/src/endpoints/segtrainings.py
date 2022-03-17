from fastapi import APIRouter, Depends, HTTPException
from main import *

router = APIRouter(prefix="/segtrain", tags=["segtrainings"])
