import json
import time
from pathlib import Path

from utils.plot import plot
from utils.evaluate import evaluate, append_metrics
from utils.plot_trace import plot_trace
from utils.runners import run_session

# Settings to run a negotiation session:
#   You need to specify the classpath of 2 agents to start a negotiation.
#   Parameters for the agent can be added as a dict (see example)
#   You need to specify the preference profiles for both agents. The first profile will be assigned to the first agent.
#   You need to specify a time deadline in milliseconds (ms).
settings = {
    "agents": [
        {
            "class": "agents.agent61.agent61.Agent61",
            "parameters": {"storage_dir": "agent_storage/Agent61"},
        },
        {
            "class": "agents.CSE3210.agent24.agent24.Agent24",
            "parameters": {"storage_dir": "agent_storage/Agent24"},
        },
    ],
    "profiles": ["domains/domain42/profileA.json", "domains/domain42/profileB.json"],
    "deadline_time_ms": 10000,
}

# run a session and obtain results in dictionaries
session_results_trace, session_results_summary = run_session(settings)

# create results directory if it does not exist
agent_a = settings["agents"][0]["class"].split(".")[-1]
agent_b = settings["agents"][1]["class"].split(".")[-1]
domain = settings["profiles"][0][8:16]
child_directory = "Session_" + domain + "_" + agent_a + "_" + agent_b + "_" + time.strftime('%Y-%m-%d-%H%M%S')
RESULTS_DIR = Path("results", child_directory)
if not RESULTS_DIR.exists():
    RESULTS_DIR.mkdir(parents=True)

# plot trace to html file
if not session_results_trace["error"]:
    plot_trace(session_results_trace, RESULTS_DIR.joinpath("trace_plot.html"))
    plot(session_results_trace, RESULTS_DIR.joinpath("plot.html"))
    res = evaluate(session_results_trace, RESULTS_DIR)

# write results to file
with open(RESULTS_DIR.joinpath("session_results_trace.json"), "w", encoding="utf-8") as f:
    f.write(json.dumps(session_results_trace, indent=2))
with open(RESULTS_DIR.joinpath("session_results_summary.json"), "w", encoding="utf-8") as f:
    f.write(json.dumps(session_results_summary, indent=2))
