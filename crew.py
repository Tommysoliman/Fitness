import json
import os
import queue
import threading
from openai import OpenAI


# ── Agent system prompts ────────────────────────────────────────────────────

COACH_SYSTEM = """You are an elite fitness coach with 20+ years of experience.

INSANITY-STYLE CARDIO/HIIT — Shaun T max-interval format:
  Warm-Up x3: jogging, jumping jacks, 1-2-3 Heisman, butt kicks, high knees, mummy kicks
  Stretch: 8-10 min full body
  Main Circuit x3 (3-4 min each, 30 sec break):
    Power Jumps, Globe Jumps, Moving Push-Ups, Suicide Drills,
    Level 2 Drills, Ski Down Abs, Squat Push-Ups, Hit the Floor,
    V Push-Ups, Tricep Ball Push-Ups, C-Sits, Ski Abs
  Cool-Down: light stretch

GYM BUILD MUSCLE — Muscle & Strength 4-day split, 3 sets, 90 sec rest:
  Day 1 Chest & Side Delts:
    Incline Barbell Bench Press 3×12,10,12 | Flat DB Bench 3×12,10,15
    Cable Crossover 3×12,12,12 | Seated Lateral Raise 3×12,12,12
    Single Arm Cable Lateral Raise 3×12,12,12
  Day 2 Upper Back & Rear Delts:
    Bent-Over Barbell Row 3×12,10,12 | DB Pullover 3×12,10,15
    Wide Grip Lat Pulldown 3×12,12,12 | DB Rear Delt Fly 3×12,12,12
    Cable Face Pull 3×12,12,12 | DB Shrug 3×12,12,12
  Day 3 Arms & Abs:
    Close Grip Bench Press 3×12,10,12 | Weighted Dip 3×12,10,12
    Rope Tricep Extension 3×12,12,12 | Lying Leg Raise 3×12,12,12
    Cable Crunch 3×12,12,12 | Barbell Curl 3×12,12,12
    Hammer Curl 3×12,10,12 | Cable Curl 3×12,12,12
  Day 4 Legs:
    Romanian Deadlift 3×12,10,12 | Lying Leg Curl 3×12,10,12
    Walking Lunge 3×12,12,12 | Front Squat 3×12,12,12
    Leg Extension 3×12,12,12 | DB Side Lunge 3×12,12,12
    Seated Calf Raise 3×12,12,12 | Calf Press 3×12,12,12
  Important: NEVER recommend Deadlifts. Never use *, +, ^, or the words "drop set" — plain English only.

BODYWEIGHT — push-ups, pull-ups, dips, squats, lunges, planks, burpees, mountain climbers.

LOSE WEIGHT — Shortcut to Shred 6-day split with after-set cardio:
  Replace ALL rest periods with 1 minute of exercise after each set.
  Exercise options (vary each session): running in place, jump rope, squat jumps, mountain climbers, burpees, lunge jumps, box jumps, jumping jacks.
  Day 1: Chest, Triceps, Abs (Multi-Joint) | Day 2: Shoulders, Legs, Calves (Multi-Joint) | Day 3: Back, Traps, Biceps (Multi-Joint)
  Day 4: Chest, Triceps, Abs (Single Joint) | Day 5: Shoulders, Legs, Calves (Single Joint) | Day 6: Back, Traps, Biceps (Single Joint)
  Progressive rep ranges: Week 1=9-11 | Week 2=6-8 | Week 3=12-15 | Week 4=16-20
  NEVER recommend Deadlifts — replace with Romanian Deadlift or Leg Press.

RUNNING — 20-Week Marathon Training Plan (HOKA):
  Phase 1 Weeks 1–8: Base Mileage — easy runs Tue/Wed/Thu, long run Sat, cross-train Sun.
  Phase 2 Weeks 9–16: Speedwork and Tempo — 400m intervals at 5K pace, tempo runs, long runs up to 29 km with tempo segments.
  Phase 3 Weeks 17–20: Peak and Taper — 32 km peak on Week 17, taper to race day Week 20.
  All distances in km and metres. Always warm up and cool down 15 min before speedwork and tempo sessions."""

NUTRITIONIST_SYSTEM = """You are a certified sports nutritionist with a PhD in Sports Science.
Protein targets: Build Muscle 2.2g/kg | Lose Weight 2.0g/kg | Other 1.8g/kg
Hydration: 37ml/kg baseline, 500-750ml or more per hour of training
Output ONLY the meal plan sections — no BMR formulas, no calculation steps."""


# ── Prompt builders ─────────────────────────────────────────────────────────

def _workout_prompt(weight, age, height, fitness_level, location, workout_type, goal):
    if workout_type == "Running":
        return _running_prompt(weight, age, height, fitness_level, goal)
    if goal == "Lose Weight":
        return f"""Create a 4-WEEK cardio acceleration fat-loss workout plan for:
Weight: {weight}kg | Height: {height}cm | Age: {age} | Level: {fitness_level} | Location: {location} | Goal: Lose Weight

AFTER EACH SET RULE: Replace ALL rest periods with 1 minute of exercise after each set (no sitting rest).
Exercise options (vary each session): running in place, jump rope, squat jumps, mountain climbers, burpees, lunge jumps, box jumps, jumping jacks.

6 WORKOUTS PER WEEK:
  Day 1: Chest, Triceps, Abs (Multi-Joint)
  Day 2: Shoulders, Legs, Calves (Multi-Joint)
  Day 3: Back, Traps, Biceps (Multi-Joint)
  Day 4: Chest, Triceps, Abs (Single Joint)
  Day 5: Shoulders, Legs, Calves (Single Joint)
  Day 6: Back, Traps, Biceps (Single Joint)
  Day 7: Rest

PROGRESSIVE OVERLOAD — rep ranges change each week:
  Week 1: 9-11 reps | Week 2: 6-8 reps | Week 3: 12-15 reps | Week 4: 16-20 reps

Scale for {fitness_level}: Beginner=3 sets | Intermediate=3-4 sets | Advanced=4-5 sets

OUTPUT FORMAT — follow this exact structure, no exceptions:

## Week 1

> After each set: 1 minute of cardio instead of resting.

### Day 1 — Chest, Triceps & Abs (Multi-Joint)

| Exercise | Sets | Reps | After Each Set |
|---|---|---|---|
| Incline Barbell Bench Press | 3 | 9-11 | 1 min running in place |
| Flat Dumbbell Bench Press | 3 | 9-11 | 1 min jump rope |
| Dips | 4 | 9-11 | 1 min squat jumps |
| Close-Grip Bench Press | 4 | 9-11 | 1 min mountain climbers |
| Cable Crunch | 3 | 9-11 | 1 min burpees |
| Lying Leg Raise | 3 | 9-11 | 1 min lunge jumps |

### Day 2 — Shoulders, Legs & Calves (Multi-Joint)
(same table format, 6-8 exercises)

Continue this EXACT pattern for all 6 workout days and all 4 weeks.
RULES: NEVER recommend Deadlifts — replace with Romanian Deadlift or Leg Press. Never use "hypertrophy" — use "Build Muscle". Never use *, +, ^ symbols. Never write "drop set". Plain English only. Every day MUST have a Markdown table."""

    if workout_type in ("HIIT", "Cardio"):
        style = "Follow INSANITY max-interval style with warm-up, main circuit x3, cool-down."
    elif workout_type == "Weights":
        style = "Follow the 4-day hypertrophy split exactly."
    else:
        style = "Bodyweight circuit: push-ups, pull-ups, squats, lunges, planks, burpees."

    return f"""Create a 4-WEEK workout plan for:
Weight: {weight}kg | Height: {height}cm | Age: {age} | Level: {fitness_level} | Location: {location} | Type: {workout_type} | Goal: {goal}

Style: {style}

Scale for {fitness_level}: Beginner=fewer sets/longer rest | Intermediate=as written | Advanced=extra sets/shorter rest
Show progressive overload Week 1→4.

OUTPUT FORMAT — you MUST follow this exact structure, no exceptions:

## Week 1

### Day 1 — Chest & Side Delts

| Exercise | Sets | Reps | Rest |
|---|---|---|---|
| Incline Barbell Bench Press | 3 | 12, 10, 12 | 90 sec |
| Flat Dumbbell Bench Press | 3 | 12, 10, 15 | 90 sec |

### Day 2 — Upper Back & Rear Delts
(same table format)

Continue this EXACT pattern for all 4 weeks and all days.
RULES: NEVER recommend Deadlifts — replace with Romanian Deadlift or Leg Press instead. Never use the word "hypertrophy" — use "Build Muscle" instead. Never use *, +, ^ symbols. Never write "drop set". Plain English only. Every day MUST have a Markdown table."""


def _nutrition_prompt(weight, age, height, fitness_level, workout_type, goal):
    pm = 2.2 if goal == "Build Muscle" else (2.0 if goal == "Lose Weight" else 1.8)
    protein_g = round(weight * pm)
    water_l = round(weight * 0.037, 1)

    return f"""Create a meal plan for: Weight {weight}kg | Height {height}cm | Age {age} | Goal: {goal} | Workout: {workout_type}
Targets: Protein {protein_g}g/day | Water {water_l}L/day

Output ONLY these sections (no intro paragraph, start immediately with the first heading):

## Daily Nutrition Targets
One table: Protein(g) | Carbs(g) | Fats(g) | Calories | Water(L)

## Your Daily Meal Plan
7 meals: Breakfast / Mid-Morning Snack / Lunch / Pre-Workout / Post-Workout / Dinner / Bedtime Snack
Each: food + portion (g or cups) + macros P/C/F

## Best Protein Sources
Two columns: Animal-based | Plant-based (with g protein per 100g)

## Supplements
3-5 recommendations for {goal}: name, dose, timing"""


def _running_prompt(weight, age, height, fitness_level, goal):
    level_note = {
        "Beginner":     "Take walk breaks as needed. Reduce distance by 20% if too hard.",
        "Intermediate": "Follow the plan as written. Trust the progressive overload.",
        "Advanced":     "Add 4x20-second strides at the end of easy runs twice per week.",
    }.get(fitness_level, "")

    race_configs = {
        "5km": {
            "weeks": 8,
            "race": "5K (5 km)",
            "peak_long": "8 km",
            "phases": (
                "Phase 1 Weeks 1-4: Base Building — 3 easy runs per week (4-6 km each) plus a long run (up to 8 km). "
                "Phase 2 Weeks 5-7: Speed Development — add 400m intervals at 5K pace and tempo runs. "
                "Week 8: Taper and race day."
            ),
        },
        "10km": {
            "weeks": 10,
            "race": "10K (10 km)",
            "peak_long": "14 km",
            "phases": (
                "Phase 1 Weeks 1-4: Base Building — 3-4 easy runs per week (5-8 km each) plus a long run. "
                "Phase 2 Weeks 5-8: Speedwork — 400m and 800m intervals at 5K-10K pace, tempo runs, long run up to 14 km. "
                "Weeks 9-10: Taper and race day."
            ),
        },
        "21km": {
            "weeks": 16,
            "race": "Half Marathon (21.1 km)",
            "peak_long": "19 km",
            "phases": (
                "Phase 1 Weeks 1-6: Base Mileage — easy runs + long run building to 13 km. "
                "Phase 2 Weeks 7-13: Speedwork and Tempo — 400m intervals, tempo runs, long runs up to 19 km with tempo segments. "
                "Weeks 14-16: Taper and race day."
            ),
        },
    }

    cfg = race_configs.get(goal, race_configs["21km"])

    return f"""Create a {cfg['weeks']}-week training plan for a {cfg['race']}.
Runner: Weight {weight}kg | Height {height}cm | Age {age} | Level: {fitness_level}
Level note: {level_note}

Plan structure: {cfg['phases']}
Peak long run: {cfg['peak_long']}

ALL distances in km and metres. Format every week as a markdown table — no exceptions:

## Week N — Phase Name

| Monday | Tuesday | Wednesday | Thursday | Friday | Saturday | Sunday |
|--------|---------|-----------|----------|--------|----------|--------|
| content | content | content | content | content | content | content |

Rules:
- Easy runs should be conversational pace
- Warm up and cool down 10-15 min for all speedwork and tempo sessions
- Every 4th week is a recovery week with reduced distance
- Final week ends with RACE DAY on Saturday and Rest on Sunday
- After all weeks add a **Race Day Tips** section with 3 bullet points

Output all {cfg['weeks']} weeks now."""


# ── Streaming generator ──────────────────────────────────────────────────────

def stream_plans(weight, age, height, fitness_level, location, workout_type, goal):
    """Yields SSE lines, interleaving workout and nutrition chunks in real time."""
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    workout_q: queue.Queue = queue.Queue()
    nutrition_q: queue.Queue = queue.Queue()

    def _stream(messages, out_q, max_tokens=4000):
        try:
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                stream=True,
                max_tokens=max_tokens,
                temperature=0.7,
            )
            for chunk in resp:
                token = chunk.choices[0].delta.content or ""
                if token:
                    out_q.put(token)
        except Exception as e:
            out_q.put(f"\n\n**Error:** {e}")
        finally:
            out_q.put(None)  # sentinel

    workout_max_tokens = 6000 if workout_type == "Running" else 4000

    t1 = threading.Thread(target=_stream, args=([
        {"role": "system", "content": COACH_SYSTEM},
        {"role": "user",   "content": _workout_prompt(weight, age, height, fitness_level, location, workout_type, goal)},
    ], workout_q, workout_max_tokens))

    t2 = threading.Thread(target=_stream, args=([
        {"role": "system", "content": NUTRITIONIST_SYSTEM},
        {"role": "user",   "content": _nutrition_prompt(weight, age, height, fitness_level, workout_type, goal)},
    ], nutrition_q))

    t1.start()
    t2.start()

    workout_done = False
    nutrition_done = False

    while not (workout_done and nutrition_done):
        if not workout_done:
            try:
                token = workout_q.get(timeout=0.05)
                if token is None:
                    workout_done = True
                    yield f"data: {json.dumps({'type': 'workout_done'})}\n\n"
                else:
                    yield f"data: {json.dumps({'type': 'workout', 'chunk': token})}\n\n"
            except queue.Empty:
                pass

        if not nutrition_done:
            try:
                token = nutrition_q.get(timeout=0.05)
                if token is None:
                    nutrition_done = True
                    yield f"data: {json.dumps({'type': 'nutrition_done'})}\n\n"
                else:
                    yield f"data: {json.dumps({'type': 'nutrition', 'chunk': token})}\n\n"
            except queue.Empty:
                pass

    t1.join()
    t2.join()
    yield f"data: {json.dumps({'type': 'done'})}\n\n"


# ── Target body-part workout ─────────────────────────────────────────────────

def stream_target_workout(body_part):
    """Stream a focused workout for a specific body part."""
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    prompt = f"""Create a focused {body_part} workout session.

OUTPUT FORMAT — follow exactly, no exceptions:

## {body_part} Workout

| Exercise | Sets | Reps | Rest |
|---|---|---|---|
| Example Exercise | 3 | 12 | 60 sec |

Include 6-8 exercises targeting {body_part}.
After the table, add a short **Tips** section (3 bullet points) on form and technique.
RULES: NEVER recommend Deadlifts. Never use *, +, ^ symbols. Plain English only."""

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": COACH_SYSTEM},
                {"role": "user", "content": prompt},
            ],
            stream=True,
            max_tokens=1000,
            temperature=0.7,
        )
        for chunk in resp:
            token = chunk.choices[0].delta.content or ""
            if token:
                yield f"data: {json.dumps({'chunk': token})}\n\n"
    except Exception as e:
        yield f"data: {json.dumps({'chunk': f'**Error:** {e}'})}\n\n"
    finally:
        yield f"data: {json.dumps({'type': 'done'})}\n\n"


# ── Q&A streaming ────────────────────────────────────────────────────────────

def ask_agent(question, agent_type, context=""):
    """Stream an answer from the fitness coach or nutritionist."""
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    if agent_type == "fitness":
        system = COACH_SYSTEM + "\nAnswer questions about workouts, exercise technique, and training. Be concise and practical."
    else:
        system = NUTRITIONIST_SYSTEM + "\nAnswer questions about nutrition, diet, meal planning, and supplements. Be concise and practical."

    messages = [{"role": "system", "content": system}]
    if context:
        messages.append({"role": "user", "content": f"Here is the personalised plan you generated:\n\n{context[:3000]}"})
        messages.append({"role": "assistant", "content": "I have your plan. What would you like to know?"})
    messages.append({"role": "user", "content": question})

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            stream=True,
            max_tokens=600,
            temperature=0.7,
        )
        for chunk in resp:
            token = chunk.choices[0].delta.content or ""
            if token:
                yield f"data: {json.dumps({'chunk': token})}\n\n"
    except Exception as e:
        yield f"data: {json.dumps({'chunk': f'**Error:** {e}'})}\n\n"
    finally:
        yield f"data: {json.dumps({'type': 'done'})}\n\n"
