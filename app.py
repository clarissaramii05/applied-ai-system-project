from datetime import date

import streamlit as st

from pawpal_system import Owner, Pet, Task, Scheduler, Category, Priority, Recurrence
from rag import get_assistant

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")

st.markdown(
    """
Welcome to the PawPal+ starter app.

This file is intentionally thin. It gives you a working Streamlit app so you can start quickly,
but **it does not implement the project logic**. Your job is to design the system and build it.

Use this app as your interactive demo once your backend classes/functions exist.
"""
)

with st.expander("Scenario", expanded=True):
    st.markdown(
        """
**PawPal+** is a pet care planning assistant. It helps a pet owner plan care tasks
for their pet(s) based on constraints like time, priority, and preferences.

You will design and implement the scheduling logic and connect it to this Streamlit UI.
"""
    )

with st.expander("What you need to build", expanded=True):
    st.markdown(
        """
At minimum, your system should:
- Represent pet care tasks (what needs to happen, how long it takes, priority)
- Represent the pet and the owner (basic info and preferences)
- Build a plan/schedule for a day that chooses and orders tasks based on constraints
- Explain the plan (why each task was chosen and when it happens)
"""
    )

st.divider()

st.subheader("Owner & Pet")
owner_name = st.text_input("Owner name", value="Jordan")
pet_name = st.text_input("Pet name", value="Mochi")
species = st.selectbox("Species", ["dog", "cat", "other"])
budget = st.number_input(
    "Time available today (minutes)", min_value=1, max_value=1440, value=90
)

st.markdown("### Tasks")
st.caption("Add a few tasks. These become real Task objects fed into your scheduler.")

# Store real Task objects (not dicts) so we can hand them straight to the scheduler.
if "tasks" not in st.session_state:
    st.session_state.tasks = []

task_title = st.text_input("Task title", value="Morning walk")
col1, col2, col3, col4 = st.columns(4)
with col1:
    category = st.selectbox("Category", [c.value for c in Category])
with col2:
    duration = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=20)
with col3:
    priority = st.selectbox("Priority", [p.value for p in Priority], index=0)
with col4:
    recurrence = st.selectbox("Repeats", [r.value for r in Recurrence])

if st.button("Add task"):
    task = Task(
        name=task_title,
        category=Category(category),
        duration_minutes=int(duration),
        priority=Priority(priority),
        recurrence=Recurrence(recurrence),
    )
    st.session_state.tasks.append(task)

# RAG feature: pull grounded task suggestions for this species out of the
# knowledge base and fold them into the plan through the core Owner hook.
st.caption("Not sure what to add? Let PawPal suggest a starter routine from its care guide.")
if st.button(f"✨ Suggest tasks for a {species}"):
    try:
        specs = get_assistant().suggest_tasks(species)
        if not specs:
            st.info(
                f"PawPal's care guide doesn't cover '{species}' yet. "
                "Suggestions are available for dogs and cats."
            )
        else:
            # Route suggestions through the core seam so they become real Task
            # objects exactly like hand-entered ones (see Owner.add_suggested_tasks).
            temp_owner = Owner(owner_name)
            temp_pet = Pet(pet_name, species=species)
            added = temp_owner.add_suggested_tasks(temp_pet, specs)
            st.session_state.tasks.extend(added)
            st.success(
                f"Added {len(added)} suggested task(s) from PawPal's {species} care guide."
            )
    except Exception as exc:  # keep the UI alive if retrieval hiccups
        st.error(f"Could not suggest tasks right now: {exc}")

if st.session_state.tasks:
    st.write("Current tasks:")
    st.table(
        [
            {
                "Task": t.name,
                "Category": t.category.value,
                "Duration (min)": t.duration_minutes,
                "Priority": t.priority.value,
                "Repeats": t.recurrence.value,
            }
            for t in st.session_state.tasks
        ]
    )
else:
    st.info("No tasks yet. Add one above.")

st.divider()

st.subheader("Build Schedule")
st.caption("Builds an Owner + Pet from your inputs and runs the Scheduler.")

if st.button("Generate schedule"):
    if not st.session_state.tasks:
        st.warning("Add at least one task before generating a schedule.")
    else:
        # Assemble the domain objects from the UI inputs.
        owner = Owner(owner_name, available_minutes=int(budget))
        pet = Pet(pet_name, species=species)
        for task in st.session_state.tasks:
            pet.add_task(task)
        owner.add_pet(pet)

        # Run the scheduler for today.
        today = date.today()
        scheduler = Scheduler.from_owner(owner, today)
        plan = scheduler.generate_plan(today)

        st.markdown(f"#### Today's Schedule for {owner.name}")
        if plan.entries:
            st.table(
                [
                    {
                        "Time": f"{e.start_time.strftime('%H:%M')}–{e.end_time.strftime('%H:%M')}",
                        "Task": e.task.name,
                        "Duration (min)": e.task.duration_minutes,
                        "Priority": e.task.priority.value,
                    }
                    for e in plan.entries
                ]
            )
        else:
            st.info("Nothing fit in the schedule today.")

        st.caption(f"Time used: {plan.total_minutes} / {owner.available_minutes} min")

        if plan.skipped:
            st.warning(
                "Skipped (not enough time): "
                + ", ".join(t.name for t in plan.skipped)
            )

        with st.expander("Why this plan?"):
            st.text(scheduler.explain())

st.divider()

# RAG feature: retrieval-grounded Q&A over the pet-care knowledge base.
st.subheader("🔎 Ask PawPal")
st.caption(
    "Ask a routine pet-care question. Answers are retrieved from PawPal's care "
    "notes (Retrieval-Augmented Generation) and cite their source. This is "
    "general guidance, not veterinary advice."
)
question = st.text_input("Your question", value="How often should I feed my dog?")
if st.button("Ask PawPal"):
    try:
        result = get_assistant().answer(question)
    except Exception as exc:  # never let the assistant crash the app
        st.error(f"Something went wrong answering that: {exc}")
    else:
        if result.guardrail == "emergency":
            st.error(result.text)  # emergency deflection stands out in red
        elif result.grounded:
            st.markdown(result.text)
            caption = f"Confidence: {result.confidence:.2f}"
            if result.sources:
                caption += "  |  Sources: " + ", ".join(result.sources)
            st.caption(caption)
        else:
            st.warning(result.text)  # empty / too-long / low-confidence
