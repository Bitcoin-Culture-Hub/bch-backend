from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

router = APIRouter(prefix="/users", tags=["Users"])

# @router.get("/", response_model=list[schemas.UserOut])
# def get_users(db: Session = Depends(get_db)):
#     return db.query(models.User).all()