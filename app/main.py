from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from .auth import router as auth_router
from .routers.students import router as students_router
from .routers.users import router as users_router
from .routers.lessons import router as lessons_router
from .routers.payments import router as payments_router
from .routers.leads import router as leads_router
from .routers.tasks import router as tasks_router
from .pages.dashboard import router as dashboard_router
from .pages.calendar import router as calendar_router
from app import exceptions as exc

app = FastAPI()
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(students_router, prefix="/students", tags=["students"])
app.include_router(users_router, prefix="/users", tags=["users"])
app.include_router(lessons_router, prefix="/lessons", tags=["lessons"])
app.include_router(payments_router, prefix="/payments", tags=["payments"])
app.include_router(leads_router, prefix="/leads", tags=["leads"])
app.include_router(tasks_router, prefix="/tasks", tags=["tasks"])
app.include_router(dashboard_router, prefix="/dashboard", tags=["dashboard"])
app.include_router(calendar_router, prefix="/calender", tags=["calender"])

@app.get("/")
async def root():
    return {"message": "Hello Worldsds"}

# статус для каждой ошибки 
ERROR_STATUS: dict[type[exc.DomainError], int] = {
    exc.PaymentNotFoundError: 404,
    exc.LessonNotFoundError: 404,
    exc.StudentNotFoundError: 404,
    exc.PaymentAlreadyExistsError: 409,
    exc.PaymentNotPendingError: 409,
    exc.PaymentStudentMismatchError: 409,
    exc.LessonAlreadyPaidError: 400,
    exc.PaymentInvalidAmountError: 400,
    exc.PaymentMethodNotAllowedError: 400,
    exc.PaymentStripeError: 502,
    exc.LessonOverlapError: 409,
    exc.LessonTimeError: 422,
    exc.LessonAlreadyCompletedError: 409,
    exc.LessonCanceledError: 409
}

def _make_handler(status_code: int):
    async def handler(request: Request, error: exc.DomainError) -> JSONResponse: 
        return JSONResponse(status_code=status_code, content={"detail": str(error)})
    return handler # типа ExceptionHandler

for error_type, status_code in ERROR_STATUS.items():
    app.add_exception_handler(error_type, _make_handler(status_code)) # принимает ExceptionHandler