class DomainError(Exception):
    pass

# Платежи

class PaymentError(DomainError):
    pass

class PaymentNotFoundError(PaymentError):
    def __init__(self, payment_id: int | None = None):
        super().__init__("Payment not found")
        self.payment_id = payment_id

class PaymentAlreadyExistsError(PaymentError):
    def __init__(self):
        super().__init__("Payment for this lesson already exists")

class PaymentNotPendingError(PaymentError):
    def __init__(self, status: str):
        super().__init__(f"Cannot mark {status} payment as paid")
        self.status = status

class PaymentMethodNotAllowedError(PaymentError):
    def __init__(self, method: str):
        super().__init__(f"Cannot create a payment with {method} method")
        self.method = method

class PaymentStudentMismatchError(PaymentError):
    def __init__(self):
        super().__init__("Student does not match the lesson")

class PaymentStripeError(PaymentError):
    def __init__(self, reason: str):
        super().__init__(f"Stripe error: {reason}")
        self.reason = reason

class PaymentInvalidAmountError(PaymentError):
    def __init__(self):
        super().__init__("Lesson price must be greater than zero to charge")

class PaymentWebhookMismatchError(PaymentError):
    def __init__(self, expected: int, received: int):
        super().__init__(f"Expected {expected} cents, got {received}")
        self.expected = expected
        self.received = received

# Занятия

class LessonError(DomainError):
    pass

class LessonTimeError(LessonError):
    def __init__(self):
        super().__init__("Lesson start must be before end")
        
class LessonNotFoundError(LessonError):
    def __init__(self, lesson_id: int | None = None):
        super().__init__("Lesson not found")
        self.lesson_id = lesson_id

class LessonAlreadyPaidError(LessonError):
    def __init__(self):
        super().__init__("Lesson is paid")

class LessonOverlapError(LessonError):
    def __init__(self):
        super().__init__("Lesson time overlaps with an existing lesson")

# Студенты

class StudentError(DomainError):
    pass

class StudentNotFoundError(StudentError):
    def __init__(self, student_id: int | None = None):
        super().__init__("Student not found for this tutor")
        self.student_id = student_id

# Тьюторы

class TutorError(DomainError):
    pass

class TutorNotFoundError(TutorError):
    def __init__(self, tutor_id: int | None = None):
        super().__init__("Tutor not found")
        self.tutor_id = tutor_id

# Баланс

class BalanceError(DomainError):
    pass