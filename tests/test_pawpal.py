"""Basic tests for PawPal+ core behaviors.

Run from the project root with:  python -m pytest
"""

from pawpal_system import Pet, Task, Category, Priority


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
