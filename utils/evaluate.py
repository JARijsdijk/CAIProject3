import json
import math
from pathlib import Path
from collections import defaultdict

import pandas as pd


def distance(x, y) -> float:
    """
    Calculate the distance between the two specified utilities.
    The distance is defined as the Euclidean distance between the points x and y,
    where each point is a two-dimensional list.

    Args:
        x: the first utility, as list where x[0] is the utility of agent A and x[1] is the utility of agent B.
        y: the second utility, as list where y[0] is the utility of agent A and y[1] is the utility of agent B.
    Return:
        A float representing the distance.
    """
    return math.dist(x, y)


def distance_pareto(utility, is_b, pareto_front) -> float:
    """
    Computes the distance to the closest point on the Pareto frontier,
    based on the specified utility of the bid, where the agent's own utility does not decrease and
    the opponent's utility also does not decrease.
    This can be used as a helper function to compute the sensitive to an opponent's preferences.
    Args:
        utility: the utility of the bid, as list where utility[0] is the utility of agent A and utility[1] is the utility of agent B.
        is_b (bool): whether the bidder is agent B, set to true when the bidder is agent B and false when the bidder is agent A.
        pareto_front: the list of bids which represent the Pareto front as specified in the specials file of the domain.
    Return:
        A float representing the distance.
    """
    utility_self = utility[is_b]
    utility_opponent = utility[not is_b]
    # Create a list of candidate points which contains points on the Pareto frontier
    # where the agent's own utility does not decrease and the opponent's utility does not decrease
    candidates = []
    for point in pareto_front:
        utility_pareto = point["utility"]
        utility_pareto_self = utility_pareto[is_b]
        if utility_pareto_self >= utility_self or math.isclose(utility_pareto_self, utility_self):
            utility_pareto_opponent = utility_pareto[not is_b]
            if utility_pareto_opponent >= utility_opponent or math.isclose(utility_pareto_opponent, utility_opponent):
                candidates.append([utility_pareto_self, utility_pareto_opponent])
    # Find the closest Pareto point to the specified bid point
    bid_point = [utility_self, utility_opponent]
    d = float("inf")
    for pareto_point in candidates:
        new_d = distance(bid_point, pareto_point)
        d = min(d, new_d)
    return d


def get_percentage(x: float, y: float) -> float:
    """
    Returns the ratio x/y expressed as a fraction of 100.
    Args:
        x (float): the numerator.
        y (float): the denominator.
    Return:
        A float representing the percentage.
    """
    # Special case where no moves are made
    if y == 0:
        return 0
    return (x / y) * 100


def evaluate(results_trace: dict, output_path: Path):
    """
    Evaluates the specified negotiation trace and saves the evaluation metrics to files in the specified output path.
    This function is used to generate some helpful metrics to assist in evaluating the agents.
    These metrics are classified as evaluation metrics, which consist of
        - "domain": the domain.
        - "agent_A": the name of agent A.
        - "agent_B": the name of agent B.
        - "agreement": whether an agreement was made.
        - "agreed_by": the name of the agent which accepted an offer.
        - "utility_a": the utility (of the accepted bid) for agent A.
        - "utility_b": the utility (of the accepted bid) for agent B.
        - "distance_nash": the distance of the accepted bid from the nash.
        - "distance_kalai": the distance of the accepted bid from the kalai.
    And Dans metrics, which are asymmetric and so needs to be represented as lists (with values for each agent) with
        - "domain": the domain.
        - "agent": the agent names.
        - "num_offers": the number of offers.
        - "fortunate_%": the percentage of fortunate moves.
        - "selfish_%": the percentage of selfish moves.
        - "concession_%": the percentage of concession moves.
        - "unfortunate_%": the percentage of unfortunate moves.
        - "nice_%": the percentage of nice moves.
        - "silent_%": the percentage of silent moves.
        - "behav_sens": the sensitivity to the opponent's behaviour.
            If behav_sens<1, then an agent is more or less insensitive to the opponent’s behaviour;
            if behav_sens>1, then an agent is more or less sensitive to the opponent’s behaviour,
            with complete sensitivity for behav_sens=inf.
        - "pref_sens": the sensitivity to the opponent's preferences.
            A negotiation strategy that is perfectly sensitive to opponent’s preferences would have a pref_sens = 0.
            The higher the measure then the worse the sensitivity of the strategy.
    Args:
        results_trace (dict): a dictionary representing the negotiation trace of the current session run.
        output_path (Path): the path to the directory where the metrics should be saved.
    Return:
        A tuple containing the evaluation metrics and Dans metrics, represented as dictionaries.
    """
    # Get the names of each agent
    agents = []
    names = []
    for agent in results_trace["partyprofiles"]:
        agents.append(agent)
        names.append("_".join(str(agent).split("_")[-2:]))

    # Get the domain from the profile of agent A
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
    agreement_actor = ""

    # In the following lines of code, we assign each bid to a move class to then calculate the Dans metrics per agent
    # This involves, firstly, counting the number of negotiation moves (aka bids) per bidder
    num_moves = defaultdict(lambda: 0)
    # Then by storing the utility for agent A and agent B for the previous bid made by the bidder,
    # we can calculate the difference compared to the utility for agent A and agent B for the next bid,
    # made by the same bidder
    utility_a = defaultdict(lambda: 0.0)
    utility_b = defaultdict(lambda: 0.0)
    # We then classify the move, from the previous bid to the next bid, by looking at the difference in utility,
    # for agent A and agent B, for example if both utilities increase then the move is fortunate,
    # but if only the bidder's utility increases then the move is selfish
    # We tally the move classes per agent
    fortunate_moves = defaultdict(lambda: 0)
    selfish_moves = defaultdict(lambda: 0)
    concession_moves = defaultdict(lambda: 0)
    unfortunate_moves = defaultdict(lambda: 0)
    nice_moves = defaultdict(lambda: 0)
    silent_moves = defaultdict(lambda: 0)
    # To compute the Sensitivity to an Opponent's Preferences we need to compute the average distance from Pareto front
    # For this we use the Total distance from the Pareto Front (to be divided by number of offers to get the average)
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

            # Increment the number of moves made by the bidder
            num_moves[agent] += 1
            # Calculate the difference in the utilities of the previous bid made by the bidder and the current bid
            delta_a = new_utility_a - utility_a[agent]
            delta_b = new_utility_b - utility_b[agent]
            # Write deltas to a file
            with open(output_path.joinpath(f"deltas_{names[agents.index(agent)]}.csv"), "a", encoding="utf-8") as f:
                f.write(f"{delta_a}, {delta_b}\n")

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
            utility = []
            for _, util in accept["utilities"].items():
                utility.append(util)
            agreement_utility = utility

    # Create a dictionary containing the evaluation metrics
    evaluation_metrics = {
        "domain": domain,
        "agent_A": names[0],
        "agent_B": names[1],
        "agreement": agreement,
        "agreed_by": agreement_actor,
        "utility_a": agreement_utility[0],
        "utility_b": agreement_utility[1],
        "distance_nash": distance(agreement_utility, nash_utility),
        "distance_kalai": distance(agreement_utility, kalai_utility),
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
            behav_sens = float(numerator) / float(denominator)
        dans_metrics["behav_sens"].append(behav_sens)
        # Sensitivity to Opponent's Preferences
        average_distance_from_pareto = total_distance[agent] / float(num_offers) if num_offers != 0 else total_distance[agent]
        dans_metrics["pref_sens"].append(average_distance_from_pareto)

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
