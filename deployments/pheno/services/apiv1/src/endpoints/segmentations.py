from fastapi import APIRouter, Depends, HTTPException

router = APIRouter(prefix="/segment", tags=["segmentations"])
