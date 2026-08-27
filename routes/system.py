import os
from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def root():
    return {"message": f"Welcome to {os.getenv('PROJECT_NAME')} AI Agent!"}
