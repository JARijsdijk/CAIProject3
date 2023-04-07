import json
import os
from pathlib import Path
import time

from utils.runners import run_tournament

RESULTS_DIR = Path("results", "Tournament_" + time.strftime('%Y-%m-%d-%H%M%S'))

# create results directory if it does not exist
if not RESULTS_DIR.exists():
    RESULTS_DIR.mkdir(parents=True)

# Settings to run a negotiation session:
#   You need to specify the classpath of 2 agents to start a negotiation.
#   Parameters for the agent can be added as a dict (see example).
#   You need to specify the preference profiles for both agents.
#   The first profile will be assigned to the first agent.
#   You need to specify a time deadline in milliseconds (ms).
tournament_settings = {
    "agents": [
        {
            "class": "agents.agent61.agent61.Agent61",
        },
        {
            "class": "agents.linear_agent.linear_agent.LinearAgent",
        },
        {
            "class": "agents.hardliner_agent.hardliner_agent.HardlinerAgent",
        },
        {
            "class": "agents.random_agent.random_agent.RandomAgent",
        },
        {
            "class": "agents.CSE3210.agent24.agent24.Agent24",
        },
    ],
    "profile_sets": [
        ["domains/domain00/profileA.json", "domains/domain00/profileB.json"],
        ["domains/domain02/profileA.json", "domains/domain02/profileB.json"],
        ["domains/domain03/profileA.json", "domains/domain03/profileB.json"],
        ["domains/domain16/profileA.json", "domains/domain16/profileB.json"],
        ["domains/domain21/profileA.json", "domains/domain21/profileB.json"],
        ["domains/domain37/profileA.json", "domains/domain37/profileB.json"],
        ["domains/domain42/profileA.json", "domains/domain42/profileB.json"],
    ],
    "deadline_time_ms": 10000,
}

# run a session and obtain results in dictionaries
tournament_steps, tournament_results, tournament_results_summary = run_tournament(tournament_settings, RESULTS_DIR)

# save the tournament settings for reference
with open(RESULTS_DIR.joinpath("tournament_steps.json"), "w", encoding="utf-8") as f:
    f.write(json.dumps(tournament_steps, indent=2))
# save the tournament results
with open(RESULTS_DIR.joinpath("tournament_results.json"), "w", encoding="utf-8") as f:
    f.write(json.dumps(tournament_results, indent=2))
# save the tournament results summary
tournament_results_summary.to_csv(RESULTS_DIR.joinpath("tournament_results_summary.csv"))
