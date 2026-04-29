from flask import Flask, render_template, request, Response, stream_with_context
import os
from dotenv import load_dotenv
from crew import stream_plans, ask_agent

load_dotenv()

app = Flask(__name__)


@app.route("/")
def index():
    resp = render_template("index.html")
    from flask import make_response
    r = make_response(resp)
    r.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    r.headers["Pragma"] = "no-cache"
    return r


@app.route("/generate", methods=["POST"])
def generate():
    data = request.get_json()

    if not os.getenv("OPENAI_API_KEY"):
        return {"error": "OpenAI API key not configured."}, 500

    weight        = float(data.get("weight", 75))
    age           = int(data.get("age", 28))
    fitness_level = data.get("fitness_level", "Intermediate")
    location      = data.get("location", "Gym")
    workout_type  = data.get("workout_type", "Weights")
    goal          = data.get("goal", "Build Muscle")

    def event_stream():
        yield from stream_plans(weight, age, fitness_level, location, workout_type, goal)

    return Response(
        stream_with_context(event_stream()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json()
    question   = data.get("question", "")
    agent_type = data.get("agent_type", "fitness")
    context    = data.get("context", "")

    def event_stream():
        yield from ask_agent(question, agent_type, context)

    return Response(
        stream_with_context(event_stream()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
