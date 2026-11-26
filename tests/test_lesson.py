import asyncio

from factories import add_lesson, get_lessons

N = 12

async def test_race_create_overlapping_lesson(session_factory, seeded):
    barrier = asyncio.Barrier(N)
    results = await asyncio.gather(
        *[add_lesson(session_factory, seeded, barrier) for _ in range(N)],
        return_exceptions=True,
    )

    errors = [r for r in results if isinstance(r, Exception)]
    assert not errors, errors
    assert results.count(True) == 1
    assert results.count(False) == N - 1

    tutor_id, student_id = seeded
    async with session_factory() as db:
        lessons = await get_lessons(db, tutor_id, student_id)
        assert len(lessons) == 1
