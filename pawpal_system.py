"""PawPal+ system skeleton.

Class stubs generated from diagrams/uml.mmd. No scheduling logic yet:
methods raise NotImplementedError so the shape is clear and the tests fail
loudly until each behavior is implemented.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date as Date, time as Time
from enum import Enum


class Priority(Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Category(Enum):
    WALK = "walk"
    FEEDING = "feeding"
    MEDS = "meds"
    ENRICHMENT = "enrichment"
    GROOMING = "grooming"


class Recurrence(Enum):
    ONCE = "once"
    DAILY = "daily"
    WEEKLY = "weekly"


@dataclass
class Task:
    """A single pet care task the owner wants done."""

    name: str
    category: Category
    duration_minutes: int
    priority: Priority
    recurrence: Recurrence = Recurrence.ONCE
    done: bool = False

    def mark_done(self) -> None:
        """Flag this task as completed."""
        raise NotImplementedError

    def is_due_today(self, on: Date) -> bool:
        """Return True if this task should run on the given date."""
        raise NotImplementedError


@dataclass
class Pet:
    """The animal being cared for."""

    name: str
    species: str
    breed: str = ""
    age: int = 0
    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        """Attach a care task to this pet."""
        raise NotImplementedError

    def remove_task(self, task: Task) -> None:
        """Detach a care task from this pet."""
        raise NotImplementedError

    def list_tasks(self) -> list[Task]:
        """Return all tasks for this pet."""
        raise NotImplementedError


@dataclass
class Owner:
    """The pet owner, who supplies constraints and preferences."""

    name: str
    available_minutes: int = 0
    preferences: list[str] = field(default_factory=list)
    pets: list[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        """Register a pet under this owner."""
        raise NotImplementedError

    def list_pets(self) -> list[Pet]:
        """Return all pets this owner has."""
        raise NotImplementedError

    def set_time_budget(self, minutes: int) -> None:
        """Set how many minutes are available for care today."""
        raise NotImplementedError


@dataclass
class PlanEntry:
    """One time-boxed slot in a daily plan."""

    start_time: Time
    end_time: Time
    task: Task

    def duration(self) -> int:
        """Return the length of this slot in minutes."""
        raise NotImplementedError


@dataclass
class DailyPlan:
    """The generated schedule for a single day."""

    plan_date: Date
    entries: list[PlanEntry] = field(default_factory=list)
    skipped: list[Task] = field(default_factory=list)
    total_minutes: int = 0

    def add_entry(self, entry: PlanEntry) -> None:
        """Add a scheduled slot to the plan."""
        raise NotImplementedError

    def list_skipped(self) -> list[Task]:
        """Return tasks that did not fit in the plan."""
        raise NotImplementedError

    def render(self) -> str:
        """Return a human-readable version of the plan for display."""
        raise NotImplementedError


class Scheduler:
    """Turns a pool of tasks into an ordered daily plan under a time budget."""

    def __init__(self, tasks: list[Task], available_minutes: int) -> None:
        self.tasks = tasks
        self.available_minutes = available_minutes

    def sort_tasks(self) -> list[Task]:
        """Order tasks by priority (and any tie-breakers)."""
        raise NotImplementedError

    def filter_by_time(self) -> list[Task]:
        """Drop tasks that do not fit within the time budget."""
        raise NotImplementedError

    def generate_plan(self, on: Date) -> DailyPlan:
        """Build and return the daily plan for the given date."""
        raise NotImplementedError

    def explain(self) -> str:
        """Explain why the plan was ordered and what was skipped."""
        raise NotImplementedError
