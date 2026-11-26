from app.models import StudentStatus
from datetime import date

def change_student_data(lesson_day: date, last_study: date | None, status: StudentStatus) -> dict:
    data = {}
    if last_study is None or lesson_day > last_study:
        data["date_of_last_study"] = lesson_day
    if status == StudentStatus.LEAD_BEFORE:
        data["status"] = StudentStatus.LEAD_APPOINTED
    elif status == StudentStatus.ARCHIVED:
        data["status"] = StudentStatus.ACTIVE
    return data