from fastapi import APIRouter, Depends, HTTPException

router = APIRouter(prefix="/classify", tags=["classifications"])
