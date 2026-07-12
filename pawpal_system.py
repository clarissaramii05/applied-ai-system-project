"""PawPal+ system.

Core classes for the pet care planner, generated from diagrams/uml.mmd.
Task, Pet, Owner, and Scheduler are implemented; PlanEntry and DailyPlan
are still simple data holders with a couple of helper stubs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date as Date, time as Time, datetime, timedelta
from enum import Enum


class Priority(Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

    @property
    def rank(self) -> int:
        """Numeric weight so tasks sort high -> low. Higher means more urgent."""
        return {"high": 3, "medium": 2, "low": 1}[self.value]


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
        self.done = True

    def is_due_today(self, on: Date) -> bool:
        """Return True if the task is unfinished and due on the given date (weekly defaults to Mondays)."""
        if self.done:
            return False
        if self.recurrence is Recurrence.ONCE:
            return True
        if self.recurrence is Recurrence.DAILY:
            return True
        if self.recurrence is Recurrence.WEEKLY:
            return on.weekday() == 0  # Monday
        return False


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
        self.tasks.append(task)

    def remove_task(self, task: Task) -> None:
        """Detach a care task from this pet (no error if it is not there)."""
        if task in self.tasks:
            self.tasks.remove(task)

    def list_tasks(self) -> list[Task]:
        """Return a copy of this pet's tasks so callers cannot mutate ours."""
        return list(self.tasks)


@dataclass
class Owner:
    """The pet owner, who supplies constraints and preferences."""

    name: str
    available_minutes: int = 0
    preferences: list[str] = field(default_factory=list)
    pets: list[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        """Register a pet under this owner."""
        self.pets.append(pet)

    def list_pets(self) -> list[Pet]:
        """Return a copy of this owner's pets."""
        return list(self.pets)

    def set_time_budget(self, minutes: int) -> None:
        """Set how many minutes are available for care today."""
        if minutes < 0:
            raise ValueError("Time budget cannot be negative.")
        self.available_minutes = minutes

    def collect_tasks(self, on: Date) -> list[Task]:
        """Gather every pet's tasks that are due on the given date to feed the Scheduler."""
        due: list[Task] = []
        for pet in self.pets:
            for task in pet.tasks:
                if task.is_due_today(on):
                    due.append(task)
        return due


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
    """Turns a pool of tasks into an ordered daily plan under a time budget.

    This is the brain of the app: it retrieves the tasks, organizes them by
    priority, and fits as many as it can into the available time.
    """

    #: When the plan day starts. Tasks get laid out back to back from here.
    DAY_START: Time = Time(8, 0)

    def __init__(self, tasks: list[Task], available_minutes: int) -> None:
        """Store the task pool and the time budget to plan within."""
        self.tasks = tasks
        self.available_minutes = available_minutes

    @classmethod
    def from_owner(cls, owner: Owner, on: Date) -> "Scheduler":
        """Build a scheduler from an owner's due tasks across all their pets for the given day."""
        return cls(tasks=owner.collect_tasks(on), available_minutes=owner.available_minutes)

    def sort_tasks(self) -> list[Task]:
        """Order tasks by priority (high first), then shortest duration as a tie-breaker."""
        return sorted(
            self.tasks,
            key=lambda t: (-t.priority.rank, t.duration_minutes),
        )

    def filter_by_time(self) -> list[Task]:
        """Return the sorted tasks that fit within the time budget, highest priority first."""
        kept: list[Task] = []
        remaining = self.available_minutes
        for task in self.sort_tasks():
            if task.duration_minutes <= remaining:
                kept.append(task)
                remaining -= task.duration_minutes
        return kept

    def generate_plan(self, on: Date) -> DailyPlan:
        """Build the daily plan: fit tasks into time slots, skip the rest."""
        plan = DailyPlan(plan_date=on)
        cursor = datetime.combine(on, self.DAY_START)
        remaining = self.available_minutes
        for task in self.sort_tasks():
            if task.duration_minutes <= remaining:
                start = cursor.time()
                cursor += timedelta(minutes=task.duration_minutes)
                plan.entries.append(
                    PlanEntry(start_time=start, end_time=cursor.time(), task=task)
                )
                plan.total_minutes += task.duration_minutes
                remaining -= task.duration_minutes
            else:
                plan.skipped.append(task)
        return plan

    def explain(self) -> str:
        """Explain, in plain language, how the plan was built."""
        lines = [
            f"Planning with a {self.available_minutes} minute budget.",
            "Tasks are ordered by priority (high first), then shortest duration.",
        ]
        remaining = self.available_minutes
        for task in self.sort_tasks():
            label = f"{task.name} ({task.duration_minutes} min, {task.priority.value})"
            if task.duration_minutes <= remaining:
                remaining -= task.duration_minutes
                lines.append(f"- Kept {label}; {remaining} min left.")
            else:
                lines.append(f"- Skipped {label}; not enough time left.")
        return "\n".join(lines)
