import json
import math
import os
from pathlib import Path
from collections import defaultdict

import plotly.graph_objects as go
from plotly.graph_objs import Figure


def evaluate(results_trace: dict, output_file: str):
    # Get the names of each party
    parties = []
    for party in results_trace["partyprofiles"]:
        parties.append(party)

    # Get the profiles and domain
    profile_a_filepath = results_trace["partyprofiles"][parties[0]]["profile"][5:]
    domain = profile_a_filepath[8:16]

    specials_filepath = Path("domains/" + domain + "/specials.json")
    with open(specials_filepath, "r") as f:
        specials = json.load(f)
        kalai = specials["kalai"]
        nash = specials["nash"]

    utility_a = defaultdict(lambda: 0.0)
    utility_b = defaultdict(lambda: 0.0)

    fortunate_moves = defaultdict(lambda: 0)
    selfish_moves = defaultdict(lambda: 0)
    concession_moves = defaultdict(lambda: 0)
    unfortunate_moves = defaultdict(lambda: 0)
    nice_moves = defaultdict(lambda: 0)
    silent_moves = defaultdict(lambda: 0)

    for action in results_trace["actions"]:
        if "Offer" in action:
            offer = action["Offer"]
            actor = offer["actor"]
            utility = []
            for _, util in offer["utilities"].items():
                utility.append(util)
            new_utility_a = utility[0]
            new_utility_b = utility[1]
            delta_a = new_utility_a - utility_a[actor]
            delta_b = new_utility_b - utility_b[actor]
            if delta_a > 0 and delta_b > 0:
                fortunate_moves[actor] = fortunate_moves[actor] + 1
            if delta_a > 0 and delta_b <= 0:
                selfish_moves[actor] = selfish_moves[actor] + 1
            if delta_a > 0 and delta_b >= 0:
                concession_moves[actor] = concession_moves[actor] + 1
            if delta_a <= 0 and delta_b < 0:
                unfortunate_moves[actor] = unfortunate_moves[actor] + 1
            if math.isclose(delta_a, 0) and delta_b > 0:
                nice_moves[actor] = nice_moves[actor] + 1
            if math.isclose(delta_a, 0) and math.isclose(delta_b, 0):
                silent_moves[actor] = silent_moves[actor] + 1
            utility_a[actor] = new_utility_a
            utility_b[actor] = new_utility_b
            # print((delta_a, delta_b))
        elif "Accept" in action:
            accept = action["Accept"]

    for party in parties:
        print(party)
        print(fortunate_moves[party])
        print(selfish_moves[party])
        print(concession_moves[party])
        print(unfortunate_moves[party])
        print(nice_moves[party])
        print(silent_moves[party])

