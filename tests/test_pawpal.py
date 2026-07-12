"""Basic tests for PawPal+ core behaviors.

Run from the project root with:  python -m pytest
"""

from datetime import date, timedelta

from pawpal_system import Pet, Task, Category, Priority, Recurrence


def test_task_completion_changes_status():
    """Calling mark_done() should flip the task from not done to done."""
    task = Task("Morning walk", Category.WALK, 30, Priority.HIGH)
    assert task.done is False  # starts incomplete

    task.mark_done()

    assert task.done is True


def test_adding_task_increases_pet_task_count():
    """Adding a task to a pet should grow that pet's task list by one."""
    pet = Pet("Mochi", species="dog")
    assert len(pet.list_tasks()) == 0

    pet.add_task(Task("Feeding", Category.FEEDING, 10, Priority.HIGH))

    assert len(pet.list_tasks()) == 1


def test_completing_daily_task_spawns_next_day():
    """Finishing a daily task should add a fresh copy due one day later."""
    pet = Pet("Mochi", species="dog")
    today = date(2026, 7, 11)
    pet.add_task(
        Task("Walk", Category.WALK, 30, Priority.HIGH,
             recurrence=Recurrence.DAILY, due_date=today)
    )

    pet.list_tasks()[0].mark_done()

    tasks = pet.list_tasks()
    assert len(tasks) == 2  # original + next occurrence
    next_task = tasks[1]
    assert next_task.done is False
    assert next_task.due_date == today + timedelta(days=1)


def test_completing_weekly_task_spawns_next_week():
    """Finishing a weekly task should add a fresh copy due seven days later."""
    pet = Pet("Luna", species="cat")
    today = date(2026, 7, 11)
    pet.add_task(
        Task("Nail trim", Category.GROOMING, 15, Priority.LOW,
             recurrence=Recurrence.WEEKLY, due_date=today)
    )

    pet.list_tasks()[0].mark_done()

    assert pet.list_tasks()[1].due_date == today + timedelta(weeks=1)


def test_one_off_task_does_not_recur():
    """A ONCE task should not create any follow-up when completed."""
    pet = Pet("Mochi", species="dog")
    pet.add_task(Task("Vet visit", Category.MEDS, 60, Priority.HIGH))

    pet.list_tasks()[0].mark_done()

    assert len(pet.list_tasks()) == 1
