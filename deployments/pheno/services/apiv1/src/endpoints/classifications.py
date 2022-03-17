from fastapi import APIRouter, Depends, HTTPException
from main import *

router = APIRouter(prefix="/classify", tags=["classifications"])
