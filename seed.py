# seed.py
from app.db import SessionLocal, Base, engine
from app.models import User
from app.utils import hash_password

# make sure tables exist
Base.metadata.create_all(bind=engine)

db = SessionLocal()

users = [
    {"username": "chandu", "email": "a@b.com", "password": "secret"},
    {"username": "alice", "email": "alice@example.com", "password": "password1"},
    {"username": "bob", "email": "bob@example.com", "password": "password2"},
]

for u in users:
    if not db.query(User).filter(User.email == u["email"]).first():
        new_user = User(
            username=u["username"],
            email=u["email"],
            hashed_password=hash_password(u["password"]),
        )
        db.add(new_user)

db.commit()
db.close()

print("Seed data inserted")