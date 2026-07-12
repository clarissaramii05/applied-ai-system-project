"""Temporary terminal testing ground for PawPal+.

Run with:  python main.py

Builds an owner with two pets, adds tasks out of chronological order, then
exercises the new sorting and filtering methods so we can confirm they work.
"""

from pawpal_system import Owner, Pet, Task, Scheduler, Category, Priority


def build_sample_owner() -> Owner:
    """Set up one owner and two pets, adding tasks deliberately out of order."""
    owner = Owner("Jordan", available_minutes=120)

    mochi = Pet("Mochi", species="dog", breed="Shiba", age=3)
    # Times are added out of order on purpose to test sort_by_time().
    mochi.add_task(Task("Evening walk", Category.WALK, 30, Priority.HIGH, time="18:00"))
    mochi.add_task(Task("Breakfast", Category.FEEDING, 10, Priority.HIGH, time="08:00"))
    mochi.add_task(Task("Midday brushing", Category.GROOMING, 20, Priority.LOW, time="13:30"))
    # Same pet, same time as the brushing above -> should trigger a conflict warning.
    mochi.add_task(Task("Give meds", Category.MEDS, 5, Priority.HIGH, time="13:30"))

    luna = Pet("Luna", species="cat", breed="Tabby", age=5)
    luna.add_task(Task("Nail trim", Category.GROOMING, 15, Priority.LOW, time="16:00"))
    luna.add_task(Task("Feed Luna", Category.FEEDING, 10, Priority.HIGH, time="07:30"))
    luna.add_task(Task("Playtime", Category.ENRICHMENT, 25, Priority.MEDIUM, time="10:00"))

    owner.add_pet(mochi)
    owner.add_pet(luna)
    return owner


def print_tasks(title: str, tasks: list[Task]) -> None:
    """Print a labeled list of tasks with their time, name, and status."""
    print(f"\n{title}")
    if not tasks:
        print("  (none)")
        return
    for task in tasks:
        status = "done" if task.done else "todo"
        print(f"  {task.time}  {task.name:<18} [{task.priority.value}] ({status})")


if __name__ == "__main__":
    owner = build_sample_owner()

    # Mark one task complete so the status filter has something to separate.
    owner.filter_by_pet("Mochi")[1].mark_done()  # Breakfast

    # Gather every task (regardless of due date) to feed the scheduler.
    all_tasks = [t for pet in owner.list_pets() for t in pet.list_tasks()]
    scheduler = Scheduler(all_tasks, owner.available_minutes)

    print("=" * 48)
    print("  PawPal+ sorting & filtering check")
    print("=" * 48)

    # 1. Sorting by time (input was out of order).
    print_tasks("Tasks in the order they were added:", all_tasks)
    print_tasks("Tasks sorted by time (sort_by_time):", scheduler.sort_by_time())

    # 2. Filtering by pet name.
    print_tasks("Only Luna's tasks (filter_by_pet):", owner.filter_by_pet("Luna"))

    # 3. Filtering by completion status.
    print_tasks("Still to do (filter_by_status=False):", owner.filter_by_status(False))
    print_tasks("Completed (filter_by_status=True):", owner.filter_by_status(True))

    # 4. Conflict detection (two tasks scheduled at the same time).
    print("\nConflict check (detect_conflicts):")
    conflicts = scheduler.detect_conflicts()
    if conflicts:
        for warning in conflicts:
            print(f"  {warning}")
    else:
        print("  No conflicts found.")
