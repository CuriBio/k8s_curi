from fastapi import APIRouter, Depends, HTTPException
from main import db

router = APIRouter(prefix="/chronus", tags=["chronus"])
