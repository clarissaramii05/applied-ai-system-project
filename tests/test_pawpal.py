"""Basic tests for PawPal+ core behaviors.

Run from the project root with:  python -m pytest
"""

from datetime import date, timedelta

from pawpal_system import Pet, Task, Scheduler, Category, Priority, Recurrence


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


def test_sort_by_time_returns_chronological_order():
    """sort_by_time() should return tasks ordered by their HH:MM time."""
    # Added deliberately out of order.
    tasks = [
        Task("Evening walk", Category.WALK, 30, Priority.HIGH, time="18:00"),
        Task("Feed", Category.FEEDING, 10, Priority.HIGH, time="07:30"),
        Task("Playtime", Category.ENRICHMENT, 25, Priority.MEDIUM, time="10:00"),
    ]
    scheduler = Scheduler(tasks, available_minutes=120)

    ordered_times = [t.time for t in scheduler.sort_by_time()]

    assert ordered_times == ["07:30", "10:00", "18:00"]


def test_detect_conflicts_flags_duplicate_times():
    """Two tasks scheduled at the same time should produce a warning."""
    tasks = [
        Task("Brushing", Category.GROOMING, 20, Priority.LOW, time="13:30"),
        Task("Give meds", Category.MEDS, 5, Priority.HIGH, time="13:30"),
    ]
    scheduler = Scheduler(tasks, available_minutes=120)

    conflicts = scheduler.detect_conflicts()

    assert len(conflicts) == 1
    assert "13:30" in conflicts[0]


def test_detect_conflicts_returns_empty_when_no_overlap():
    """Tasks at non-overlapping times should report no conflicts."""
    tasks = [
        Task("Feed", Category.FEEDING, 10, Priority.HIGH, time="08:00"),
        Task("Walk", Category.WALK, 30, Priority.HIGH, time="09:00"),
    ]
    scheduler = Scheduler(tasks, available_minutes=120)

    assert scheduler.detect_conflicts() == []
