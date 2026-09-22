from fastapi import FastAPI
from sqlalchemy.orm import Session
from routers.auth import router as auth_router
from routers.students import router as students_router
from routers.users import router as users_router
import uvicorn

app = FastAPI()
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(students_router, prefix="/students", tags=["students"])
app.include_router(users_router, prefix="/users", tags=["users"])

@app.get("/")
async def root():
    return {"message": "Hello World"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)