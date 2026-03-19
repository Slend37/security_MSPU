from fastapi import FastAPI

app = FastAPI()
from src.schemas import UserCreate

@app.post('/registration')
def index(user: UserCreate):
    return{"message": "User created", "user": user.username}
