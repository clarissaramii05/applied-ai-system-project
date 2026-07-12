# PawPal+ Project Reflection

## 1. System Design

**Core user actions**

A pet owner using PawPal+ needs to be able to do three main things:

1. Add a pet care task. The owner types in a task like a walk, feeding, meds, enrichment, or grooming, and gives it a duration and a priority. They can also edit the task later if something changes. This is the info the app needs before it can plan anything.

2. Generate a daily plan. Once the tasks are in, the owner asks the app to build a schedule. The scheduler looks at the constraints, like how much time is available and how important each task is, and turns the list of tasks into an ordered daily plan.

3. See today's plan. The owner can look at the finished schedule laid out clearly, with the time, task, duration, and priority for each item. Ideally the app also explains why it picked that order and why it skipped anything when there was not enough time.

These three actions basically form the flow of the whole app, going from input to processing to output, and they shaped how I set up my classes.

**a. Initial design**

My first UML had seven classes plus a few enums. I tried to split them up by what each one is actually responsible for instead of dumping everything into one big class.

- Owner: holds the person's info, their preferences, and the daily time budget (available_minutes). The time budget matters a lot because it is the main constraint the scheduler has to respect.
- Pet: holds the animal's info (name, species, breed, age) and the list of tasks that belong to it. I kept this separate from Owner so that later on one owner could have more than one pet.
- Task: this is the main input for everything. It holds the name, category, duration, priority, recurrence, and a done flag. It can mark itself done and check if it is due on a given day.
- Scheduler: this is the brain of the app. It takes the tasks and the time budget and does the actual work of sorting, filtering by time, generating the plan, and explaining its choices.
- DailyPlan: the output. It holds the scheduled entries, the tasks that got skipped, and the total minutes used, and it can render itself for the UI.
- PlanEntry: one time slot in the plan, so it links a task to a start and end time.
- Priority, Category, and Recurrence: I made these enums so the values stay consistent instead of me typing random strings everywhere.

The idea was that the data classes (Task, Pet, Owner, PlanEntry, DailyPlan) just hold information, and the Scheduler is the one class that actually does the thinking.

**b. Design changes**

Once I wrote out the skeleton I noticed two problems and fixed them.

The first was a missing relationship. My tasks lived on Pet and my time budget lived on Owner, but the Scheduler just took a flat list of tasks. There was nothing that actually gathered all the tasks from all the pets and handed them to the Scheduler. So if an owner had two pets I had no clean way to build the input. I added a collect_tasks(on) method to Owner that pulls together every pet's tasks that are due on a given day. That way the Owner is in charge of assembling the task pool and the UI does not have to stitch each pet's list together by hand.

The second was more of a bottleneck. My Priority enum used strings like "high" and "medium", but if I ever sort by those directly they come out in alphabetical order, which is wrong (it would put "high" before "low" before "medium"). Sorting is basically the core of the whole scheduler, so this would have quietly broken everything. I added a rank property to Priority that turns it into a number (high is 3, medium is 2, low is 1) so sort_tasks has a real ordering to sort by.

Both changes were small but they connected the classes together and made sure the most important part, the sorting, is actually reliable.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?
- How did you decide which constraints mattered most?

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.
- Why is that tradeoff reasonable for this scenario?

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- What kinds of prompts or questions were most helpful?

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
