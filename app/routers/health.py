from fastapi import APIRouter

router = APIRouter()

@router.get("/", tags=["health"])
def root():
    return {"status": "ok"}