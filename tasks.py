from crewai import Task


def create_workout_task(agent, weight, age, fitness_level, location, workout_type, goal):
    if workout_type in ("HIIT", "Cardio"):
        style_note = (
            "Follow INSANITY max-interval style: warm-up circuit × 3, full-body stretch, "
            "main circuit × 3, cool-down. Escalate intensity each week."
        )
    elif workout_type == "Weights":
        style_note = (
            "Follow the Muscle & Strength 4-day hypertrophy split exactly "
            "(Chest/Delts, Back/Rear Delts, Arms/Abs, Legs) with rest-pause (*), drop sets (+), "
            "and negatives (^). If location is Home or Garden substitute equipment with available alternatives."
        )
    else:
        style_note = (
            "Design a bodyweight circuit programme using push-ups, pull-ups, dips, squats, lunges, "
            "planks, burpees, and mountain climbers. No equipment required."
        )

    hiit_finisher = ""
    if goal == "Lose Weight":
        hiit_finisher = """
WEIGHT LOSS FINISHER (MANDATORY):
Because the goal is Lose Weight, add a 15-minute HIIT finisher at the END of exactly 3 workout days per week.
Format it as a separate section after the main workout labeled "🔥 15-Min HIIT Finisher".
Structure: 40 sec work / 20 sec rest, 3 rounds of 5 exercises.
Use exercises like: Jump Squats, Burpees, High Knees, Mountain Climbers, Lateral Skaters, Box Jumps, Tuck Jumps.
Vary the exercises each week."""

    return Task(
        description=f"""Create a complete 4-WEEK monthly workout plan for:
  Weight: {weight} kg | Age: {age} | Level: {fitness_level} | Location: {location}
  Type: {workout_type} | Goal: {goal}

Style instruction: {style_note}
{hiit_finisher}

REQUIREMENTS:
1. Produce a week-by-week calendar: Week 1 → Week 4.
2. Clearly label workout days and rest days.
3. For every workout day list:
   - Exercise name
   - Sets × Reps (e.g. 3 × 12,10,12*)
   - Rest period
   - Technique note where relevant
4. Adjust difficulty for fitness level:
   - Beginner: fewer sets, longer rest, simpler exercises
   - Intermediate: follow programme as written
   - Advanced: extra sets, shorter rest, added intensity techniques
5. Show progressive overload from Week 1 to Week 4.

Output clean, well-structured Markdown with headers for each week and day.""",
        agent=agent,
        expected_output=(
            "A 4-week workout calendar in Markdown with daily schedules, "
            "exercise names, sets/reps, rest periods, technique notes, "
            "HIIT finishers on 3 days per week if goal is Lose Weight, "
            "and weekly progression guidance."
        ),
    )


def create_nutrition_task(agent, weight, age, fitness_level, workout_type, goal):
    protein_multiplier = 2.2 if goal == "Build Muscle" else (2.0 if goal == "Lose Weight" else 1.8)
    protein_g = round(weight * protein_multiplier)
    water_l = round(weight * 0.037, 1)

    return Task(
        description=f"""Create a clean, practical meal plan for:
  Weight: {weight} kg | Age: {age} | Goal: {goal} | Workout: {workout_type}
  Protein target: {protein_g} g/day | Water: {water_l} L/day

OUTPUT ONLY the following sections — no BMR formulas, no calorie equations, no calculation steps:

## Daily Nutrition Targets
One short table: Protein (g) | Carbs (g) | Fats (g) | Calories | Water (L). Just the numbers.

## Your Daily Meal Plan
Show 7 meals/snacks: Breakfast / Mid-Morning Snack / Lunch / Pre-Workout / Post-Workout / Dinner / Bedtime Snack.
For each meal: food items, portion in grams or cups, and macros (P/C/F in grams). Keep it practical and realistic.

## Best Protein Sources
Two columns: Animal-based and Plant-based. Include protein per 100g for each.

## Hydration Schedule
Simple bullet list: when to drink and how much throughout the day.

## Pre & Post Workout Nutrition
What to eat, exact portions, and timing window for each.

## Supplements
3–5 recommendations tailored to {goal}. Name, dose, timing. No fluff.

Keep the tone direct and practical. No introductory paragraphs. Start immediately with the first section heading.""",
        agent=agent,
        expected_output=(
            "A concise meal plan in Markdown with a targets table, "
            "7-meal daily plan with macros, protein sources, "
            "hydration schedule, pre/post workout nutrition, and supplements."
        ),
    )
