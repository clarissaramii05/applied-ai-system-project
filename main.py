"""Temporary terminal testing ground for PawPal+.

Run with:  python main.py

Builds an owner with a couple of pets and some tasks, then prints the
generated daily schedule so we can eyeball whether the logic works.
"""

from datetime import date

from pawpal_system import Owner, Pet, Task, Scheduler, Category, Priority, Recurrence


def build_sample_owner() -> Owner:
    """Set up one owner, two pets, and a handful of tasks to plan."""
    owner = Owner("Jordan", available_minutes=90)

    mochi = Pet("Mochi", species="dog", breed="Shiba", age=3)
    mochi.add_task(Task("Morning walk", Category.WALK, 30, Priority.HIGH, Recurrence.DAILY))
    mochi.add_task(Task("Breakfast", Category.FEEDING, 10, Priority.HIGH, Recurrence.DAILY))
    mochi.add_task(Task("Brushing", Category.GROOMING, 20, Priority.LOW))

    luna = Pet("Luna", species="cat", breed="Tabby", age=5)
    luna.add_task(Task("Feed Luna", Category.FEEDING, 10, Priority.HIGH, Recurrence.DAILY))
    luna.add_task(Task("Play/enrichment", Category.ENRICHMENT, 25, Priority.MEDIUM))
    luna.add_task(Task("Nail trim", Category.GROOMING, 15, Priority.LOW))

    owner.add_pet(mochi)
    owner.add_pet(luna)
    return owner


def print_schedule(owner: Owner, on: date) -> None:
    """Print a clean, aligned 'Today's Schedule' for the terminal."""
    scheduler = Scheduler.from_owner(owner, on)
    plan = scheduler.generate_plan(on)

    print("=" * 44)
    print(f"  Today's Schedule for {owner.name}")
    print(f"  {on.strftime('%A, %B %d, %Y')}")
    print("=" * 44)

    if not plan.entries:
        print("  Nothing scheduled today.")
    for entry in plan.entries:
        slot = f"{entry.start_time.strftime('%H:%M')}-{entry.end_time.strftime('%H:%M')}"
        task = entry.task
        print(f"  {slot}  {task.name:<18} ({task.duration_minutes:>2} min) [{task.priority.value}]")

    print("-" * 44)
    print(f"  Time used: {plan.total_minutes} / {owner.available_minutes} min")

    if plan.skipped:
        print(f"  Skipped ({len(plan.skipped)}): " + ", ".join(t.name for t in plan.skipped))

    print("=" * 44)
    print("\nWhy this plan:")
    print(scheduler.explain())


if __name__ == "__main__":
    owner = build_sample_owner()
    print_schedule(owner, date.today())
