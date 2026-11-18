from factories import create_pending_payment, create_tutor_student, pay, AMOUNT, get_deposits, get_balances
import asyncio

async def test_race_mark_paid(session_factory):
    async with session_factory() as db:
        tutor_id, student_id = await create_tutor_student(db)
        payment_id = await create_pending_payment(db, tutor_id, student_id, amount=AMOUNT)

    results = await asyncio.gather(
        *[pay(session_factory, payment_id) for _ in range(100)],
        return_exceptions=True,
    )

    errors = [r for r in results if isinstance(r, Exception)]
    assert not errors, errors
    assert results.count(True) == 1
    assert results.count(False) == 99

    async with session_factory() as db:
        assert await get_balances(db, tutor_id, student_id) == (AMOUNT, AMOUNT)
        assert len(await get_deposits(db, payment_id)) == 1