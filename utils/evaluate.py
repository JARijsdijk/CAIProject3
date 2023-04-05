import json
import math
import os
from pathlib import Path
from collections import defaultdict

import pandas as pd
import plotly.graph_objects as go
from plotly.graph_objs import Figure


def distance(x, y) -> float:
    return math.dist(x, y)


def distance_pareto(utility, is_b, pareto_front) -> float:
    """
    Distance to the closest point on the Pareto frontier
    """
    utility_self = utility[is_b]
    utility_opponent = utility[not is_b]
    candidates = []
    for point in pareto_front:
        utility_pareto = point["utility"]
        utility_pareto_self = utility_pareto[is_b]
        if utility_pareto_self >= utility_self or math.isclose(utility_pareto_self, utility_self):
            utility_pareto_opponent = utility_pareto[not is_b]
            candidates.append([utility_pareto_self, utility_pareto_opponent])
    # Find the closest Pareto point to the bid point
    bid_point = [utility_self, utility_opponent]
    closest_point = []
    d = float("inf")
    for pareto_point in candidates:
        new_d = distance(bid_point, pareto_point)
        if new_d < d:
            closest_point = pareto_point
        d = min(d, new_d)
    # print(f"Bid point: ({bid_point[0]}, {bid_point[1]})")
    # print(f"Par point: ({closest_point[0]}, {closest_point[1]})")
    # print(f"Distance: {d}")
    return d


def get_percentage(x, y) -> str:
    z = (float(x) / float(y)) * 100
    return f"{z: .3f}"


def evaluate(results_trace: dict, output_path: Path):
    # Get the names of each agent
    agents = []
    names = []
    for agent in results_trace["partyprofiles"]:
        agents.append(agent)
        names.append("_".join(str(agent).split("_")[-2:]))

    # Get the profiles and domain
    profile_a_filepath = results_trace["partyprofiles"][agents[0]]["profile"][5:]
    domain = profile_a_filepath[8:16]

    # Get the special points from the domain
    specials_filepath = Path("domains/" + domain + "/specials.json")
    with open(specials_filepath, "r") as f:
        specials = json.load(f)
        pareto_front = specials["pareto_front"]
        kalai_utility = specials["kalai"]["utility"]
        nash_utility = specials["nash"]["utility"]

    # Declare variables used to store the acceptance values if an agreement exists
    agreement = False
    agreement_utility = [0.0, 0.0]
    # agreement_bid = None
    agreement_actor = ""

    # For each offer per agent calculate the move class
    utility_a = defaultdict(lambda: 0.0)
    utility_b = defaultdict(lambda: 0.0)
    # Count the number of moves per agent
    num_moves = defaultdict(lambda: 0)
    # Tally the move classes per agent
    fortunate_moves = defaultdict(lambda: 0)
    selfish_moves = defaultdict(lambda: 0)
    concession_moves = defaultdict(lambda: 0)
    unfortunate_moves = defaultdict(lambda: 0)
    nice_moves = defaultdict(lambda: 0)
    silent_moves = defaultdict(lambda: 0)
    # Total distance from the Pareto Front (to be divided by number of offers to get the average)
    total_distance = defaultdict(lambda: 0.0)

    for action in results_trace["actions"]:
        # Check if the action performed was an offer
        if "Offer" in action:
            offer = action["Offer"]
            # Get bidder
            agent = offer["actor"]
            # Get utility of the current bid
            utility = []
            for _, util in offer["utilities"].items():
                utility.append(util)
            new_utility_a = utility[0]
            new_utility_b = utility[1]

            # Increment the number of moves made by bidder
            num_moves[agent] += 1
            # Calculate the difference in the utilities of the previous bid made by the bidder and the current bid
            delta_a = new_utility_a - utility_a[agent]
            delta_b = new_utility_b - utility_b[agent]
            # Write deltas to file
            with open(output_path.joinpath(f"deltas_{names[agents.index(agent)]}.csv"), "a", encoding="utf-8") as f:
                f.write(f"{delta_a: .3f}, {delta_b: .3f}\n")

            # Classify and tally the move based on the difference in the utilities
            if delta_a > 0 and delta_b > 0:
                fortunate_moves[agent] += 1
            if delta_a > 0 and delta_b <= 0:
                selfish_moves[agent] += 1
            if delta_a < 0 and delta_b >= 0:
                concession_moves[agent] += 1
            if delta_a <= 0 and delta_b < 0:
                unfortunate_moves[agent] += 1
            if math.isclose(delta_a, 0) and delta_b > 0:
                nice_moves[agent] += 1
            if math.isclose(delta_a, 0) and math.isclose(delta_b, 0):
                silent_moves[agent] += 1

            # Compute the distance of the bid from the Pareto Front
            is_b = agents.index(agent)
            d = distance_pareto(utility, is_b, pareto_front)
            # Write distance to file
            with open(output_path.joinpath(f"distances_{names[agents.index(agent)]}.csv"), "a", encoding="utf-8") as f:
                f.write(f"{d}\n")
            # Add distance to the total distance
            total_distance[agent] += d

            # Overwrite the previous utilities with the current utilities
            utility_a[agent] = new_utility_a
            utility_b[agent] = new_utility_b

        # Check if the action performed was an acceptance of an offer
        elif "Accept" in action:
            accept = action["Accept"]
            agreement = True
            agent = accept["actor"]
            agreement_actor = names[agents.index(agent)]
            # agreement_bid = accept["bid"]["issuevalues"]
            utility = []
            for _, util in accept["utilities"].items():
                utility.append(util)
            agreement_utility = utility

    # Create a dictionary containing the evaluation metrics
    utility_a = f"{agreement_utility[0]:.3f}"
    utility_b = f"{agreement_utility[1]:.3f}"
    distance_nash = f"{distance(agreement_utility, nash_utility):.3f}"
    distance_kalai = f"{distance(agreement_utility, kalai_utility):.3f}"
    evaluation_metrics = {
        "domain": domain,
        "agent_A": names[0],
        "agent_B": names[1],
        "agreement": agreement,
        "agreed_by": agreement_actor,
        "utility_a": utility_a,
        "utility_b": utility_b,
        "distance_nash": distance_nash,
        "distance_kalai": distance_kalai,
    }

    # Create a dictionary containing the dans metrics
    dans_metrics = defaultdict(lambda: [])
    for agent in agents:
        # Domain
        dans_metrics["domain"].append(domain)
        # Agent names
        dans_metrics["agent"].append(names[agents.index(agent)])
        # Number of offers
        num_offers = num_moves[agent]
        dans_metrics["num_offers"].append(num_offers)
        # Percentage of fortunate moves
        fortunate = get_percentage(fortunate_moves[agent], num_offers)
        dans_metrics["fortunate_%"].append(fortunate)
        # Percentage of selfish moves
        selfish = get_percentage(selfish_moves[agent], num_offers)
        dans_metrics["selfish_%"].append(selfish)
        # Percentage of concession moves
        concession = get_percentage(concession_moves[agent], num_offers)
        dans_metrics["concession_%"].append(concession)
        # Percentage of unfortunate moves
        unfortunate = get_percentage(unfortunate_moves[agent], num_offers)
        dans_metrics["unfortunate_%"].append(unfortunate)
        # Percentage of nice moves
        nice = get_percentage(nice_moves[agent], num_offers)
        dans_metrics["nice_%"].append(nice)
        # Percentage of silent moves
        silent = get_percentage(silent_moves[agent], num_offers)
        dans_metrics["silent_%"].append(silent)
        # Sensitivity to Opponent's Behaviour
        numerator = fortunate_moves[agent] + nice_moves[agent] + concession_moves[agent]
        denominator = unfortunate_moves[agent] + silent_moves[agent] + selfish_moves[agent]
        if denominator == 0:
            behav_sens = "inf"
        else:
            behav_sens = f"{float(numerator) / float(denominator):.3f}"
        dans_metrics["behav_sens"].append(behav_sens)
        # Sensitivity to Opponent's Preferences
        average_distance_from_pareto = total_distance[agent] / float(num_offers)
        dans_metrics["pref_sens"].append(f"{average_distance_from_pareto:.3f}")

    # Write and return metrics
    metrics = (evaluation_metrics, dans_metrics)
    write_metrics(metrics, output_path)
    return metrics


def write_metrics(metrics, output_path: Path):
    evaluation_metrics = metrics[0]
    columns = evaluation_metrics.keys()
    row = evaluation_metrics.values()
    evaluation_summary = pd.DataFrame([row], columns=columns)
    evaluation_summary.to_csv(output_path.joinpath("evaluation.csv"), index=False)

    dans_metrics = metrics[1]
    dans_summary = pd.DataFrame(dans_metrics)
    dans_summary.to_csv(output_path.joinpath("dans.csv"), index=False)


def append_metrics(metrics, session_id, output_path: Path):
    evaluation_filepath = output_path.joinpath("tournament_evaluation.csv")
    evaluation_metrics = metrics[0]
    columns = list(evaluation_metrics.keys())
    row = list(evaluation_metrics.values())
    # Insert session id at the front
    columns.insert(0, "session_id")
    row.insert(0, session_id)
    evaluation_summary = pd.DataFrame([row], columns=columns)
    evaluation_summary.to_csv(evaluation_filepath, index=False, mode='a',
                              header=not evaluation_filepath.exists())

    dans_filepath = output_path.joinpath("tournament_dans.csv")
    # Insert session id at the front by recreating dictionary
    dans_metrics = defaultdict(lambda: [])
    dans_metrics["session_id"] = [session_id, session_id]
    for key, value in metrics[1].items():
        dans_metrics[key] = value
    dans_summary = pd.DataFrame(dans_metrics)
    dans_summary.to_csv(dans_filepath, index=False, mode='a', header=not dans_filepath.exists())
