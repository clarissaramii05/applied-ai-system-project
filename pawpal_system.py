"""PawPal+ system.

Core classes for the pet care planner, generated from diagrams/class_diagram.mmd.
Task, Pet, Owner, and Scheduler are implemented; PlanEntry and DailyPlan
are still simple data holders with a couple of helper stubs.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date as Date, time as Time, datetime, timedelta
from enum import Enum

#: Logger for the core domain layer. Keeps a trace of AI-suggested tasks being
#: folded into the scheduling logic (see build_task_from_spec / add_suggested_tasks).
core_logger = logging.getLogger("pawpal.core")


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
    time: str = "08:00"  # preferred time of day, "HH:MM" (24-hour)
    due_date: Date = field(default_factory=Date.today)
    # Back-reference to the owning pet, so completing a recurring task can add
    # its next occurrence to the same pet. Kept out of repr/equality.
    pet: "Pet | None" = field(default=None, repr=False, compare=False)

    def mark_done(self) -> "Task | None":
        """Mark complete; if recurring, add the next occurrence to its pet and return it."""
        self.done = True
        upcoming = self.next_occurrence()
        if upcoming is not None and self.pet is not None:
            self.pet.add_task(upcoming)
        return upcoming

    def next_occurrence(self) -> "Task | None":
        """Return a fresh, uncompleted copy due on the next date, or None if it does not repeat."""
        if self.recurrence is Recurrence.DAILY:
            step = timedelta(days=1)
        elif self.recurrence is Recurrence.WEEKLY:
            step = timedelta(weeks=1)
        else:
            return None
        return Task(
            name=self.name,
            category=self.category,
            duration_minutes=self.duration_minutes,
            priority=self.priority,
            recurrence=self.recurrence,
            done=False,
            time=self.time,
            due_date=self.due_date + step,
        )

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
        """Attach a care task to this pet and record the pet on the task."""
        task.pet = self
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

    def filter_by_status(self, done: bool) -> list[Task]:
        """Return all tasks across every pet matching the given done status."""
        return [task for pet in self.pets for task in pet.tasks if task.done == done]

    def filter_by_pet(self, pet_name: str) -> list[Task]:
        """Return all tasks belonging to the pet with the given name."""
        return [task for pet in self.pets if pet.name == pet_name for task in pet.tasks]

    def add_suggested_tasks(self, pet: Pet, specs) -> list[Task]:
        """Fold AI-suggested tasks into the scheduling logic for one of this owner's pets.

        This is the seam where the RAG feature (rag.py) meets the core system.
        It accepts plain, duck-typed suggestion specs (each exposing name,
        category, duration_minutes, priority -- see rag.TaskSpec), converts them
        into real Task objects, and registers them on the pet so they flow into
        the Scheduler exactly like hand-entered tasks. The core deliberately
        imports nothing from rag.py: suggestions arrive as data, so retrieval,
        guardrails, and logging stay isolated in the RAG layer. Invalid specs are
        skipped rather than allowed to crash planning.
        """
        built = build_tasks_from_specs(specs)
        for task in built:
            pet.add_task(task)
        core_logger.info("Added %d suggested task(s) to pet %r.", len(built), pet.name)
        return built


def _coerce_category(value: str) -> Category:
    """Map a suggestion's category string onto the Category enum, defaulting safely."""
    try:
        return Category(str(value).strip().lower())
    except (ValueError, AttributeError):
        core_logger.warning("Unknown category %r; defaulting to ENRICHMENT.", value)
        return Category.ENRICHMENT


def _coerce_priority(value: str) -> Priority:
    """Map a suggestion's priority string onto the Priority enum, defaulting safely."""
    try:
        return Priority(str(value).strip().lower())
    except (ValueError, AttributeError):
        core_logger.warning("Unknown priority %r; defaulting to MEDIUM.", value)
        return Priority.MEDIUM


def build_task_from_spec(spec) -> "Task | None":
    """Turn one duck-typed suggestion spec into a Task, or None if it is unusable.

    Accepts any object exposing name, category, duration_minutes, and priority
    (typically a rag.TaskSpec) so the core keeps no dependency on the RAG layer.
    Returning None on bad input lets the caller skip a single bad row instead of
    failing the whole suggestion batch.
    """
    try:
        name = str(spec.name).strip()
        duration = int(spec.duration_minutes)
    except (AttributeError, TypeError, ValueError):
        core_logger.warning("Skipping unparseable task spec: %r", spec)
        return None
    if not name or duration <= 0:
        core_logger.warning(
            "Skipping invalid task spec (name=%r, duration=%r).", name, duration
        )
        return None
    return Task(
        name=name,
        category=_coerce_category(getattr(spec, "category", "")),
        duration_minutes=duration,
        priority=_coerce_priority(getattr(spec, "priority", "")),
    )


def build_tasks_from_specs(specs) -> list[Task]:
    """Build Tasks from an iterable of suggestion specs, skipping invalid ones."""
    return [task for task in (build_task_from_spec(s) for s in specs) if task is not None]


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

    def sort_by_time(self) -> list[Task]:
        """Order tasks chronologically by their 'HH:MM' time attribute.

        Zero-padded 24-hour strings sort lexicographically in clock order,
        so a plain string sort on the time is all we need.
        """
        return sorted(self.tasks, key=lambda t: t.time)

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

    @staticmethod
    def _minutes(hhmm: str) -> int:
        """Convert an 'HH:MM' time string into minutes since midnight."""
        hours, minutes = hhmm.split(":")
        return int(hours) * 60 + int(minutes)

    @staticmethod
    def _owner_of(task: Task) -> str:
        """Return the owning pet's name, or a placeholder if unassigned."""
        return task.pet.name if task.pet is not None else "unassigned"

    def detect_conflicts(self) -> list[str]:
        """Return warning messages for tasks whose time slots overlap.

        Each task covers [start, start + duration). Two tasks conflict when
        one starts before the other ends, whether they belong to the same
        pet or different pets. Returns messages (empty list if none) instead
        of raising, so the caller can warn the user and keep running.
        """
        warnings: list[str] = []
        ordered = self.sort_by_time()
        for i in range(len(ordered)):
            for j in range(i + 1, len(ordered)):
                first, second = ordered[i], ordered[j]
                first_start = self._minutes(first.time)
                first_end = first_start + first.duration_minutes
                second_start = self._minutes(second.time)
                second_end = second_start + second.duration_minutes
                if first_start < second_end and second_start < first_end:
                    same = first.pet is not None and first.pet is second.pet
                    whose = "same pet" if same else "different pets"
                    warnings.append(
                        f"WARNING - conflict ({whose}): "
                        f"'{first.name}' for {self._owner_of(first)} at {first.time} "
                        f"overlaps '{second.name}' for {self._owner_of(second)} at {second.time}."
                    )
        return warnings

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
