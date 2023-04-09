import csv
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd


def main():
    # Get all tournament directories in the results directory
    results_dir = Path("../results/")
    tournament_dir_list: [Path] = [f for f in results_dir.iterdir() if f.is_dir() and "Tournament" in f.name]

    # Get a list of all tournament evaluation and dans metrics
    evaluation_list = []
    dans_list = []
    num_tournaments = len(tournament_dir_list) * 2
    print(f"Number of Tournaments: {num_tournaments}")
    num_sessions = 0
    for tournament_dir in tournament_dir_list:
        evaluation_csv_file = tournament_dir.joinpath("tournament_evaluation.csv")
        with open(evaluation_csv_file, newline='') as csvfile:
            tournament_evaluation = list(csv.DictReader(csvfile))
            evaluation_list.append(tournament_evaluation)
            if not num_sessions:
                num_sessions = len(tournament_evaluation)
                print(f"Number of Sessions: {num_sessions}")

        dans_csv_file = tournament_dir.joinpath("tournament_dans.csv")
        with open(dans_csv_file, newline='') as csvfile:
            tournament_dans = list(csv.DictReader(csvfile))
            dans_list.append(tournament_dans)

    # Compute the totals of the evaluation metrics per domain for each tournament
    num_domains = 50
    evaluation_totals = [defaultdict(lambda: 0.0) for i in np.arange(num_domains)]
    for evaluation in evaluation_list:
        for session in evaluation:
            domain_id = int(session["domain"][-2:])
            agreement = session["agreement"] == "True"
            if agreement:
                # Increment the count of the agreements reached
                evaluation_totals[domain_id]["num_agreements"] += 1
                # Add the utility of agent A
                evaluation_totals[domain_id]["utility_a"] += float(session["utility_a"])
                # Add the utility of agent b
                evaluation_totals[domain_id]["utility_b"] += float(session["utility_b"])
                # Add the distance from Nash
                evaluation_totals[domain_id]["distance_nash"] += float(session["distance_nash"])
                # Add the distance from Kalai
                evaluation_totals[domain_id]["distance_kalai"] += float(session["distance_kalai"])

    # Generate a dictionary that represents the aggregation of the evaluation metrics
    evaluation_aggregate = defaultdict(lambda: [])
    for domain_id, domain_totals in enumerate(evaluation_totals):
        # Domain
        evaluation_aggregate["domain"].append(domain_id)
        # Number of Agreements
        num_agreements = domain_totals["num_agreements"]
        evaluation_aggregate["num_agreements"].append(num_agreements)
        # Average utility of agent A
        total_utility_a = float(domain_totals["utility_a"])
        utility_a = total_utility_a / num_agreements if num_agreements != 0 else 0
        evaluation_aggregate["utility_a"].append(utility_a)
        # Average utility of agent B
        total_utility_b = float(domain_totals["utility_b"])
        utility_b = total_utility_b / num_agreements if num_agreements != 0 else 0
        evaluation_aggregate["utility_b"].append(utility_b)
        # Average distance from Nash
        total_distance_nash = float(domain_totals["distance_nash"])
        distance_nash = total_distance_nash / num_agreements if num_agreements != 0 else 0
        evaluation_aggregate["distance_nash"].append(distance_nash)
        # Average distance from Kalai
        total_distance_kalai = float(domain_totals["distance_kalai"])
        distance_kalai = total_distance_kalai / num_agreements if num_agreements != 0 else 0
        evaluation_aggregate["distance_kalai"].append(distance_kalai)

    # Write aggregate of the evaluation metrics to a csv file
    evaluation_summary = pd.DataFrame(evaluation_aggregate)
    evaluation_summary.to_csv(results_dir.joinpath("aggregate_evaluation.csv"), index=False)

    # Compute the totals of the Dans metrics per domain for each tournament
    dans_totals = [defaultdict(lambda: defaultdict(lambda: 0.0)) for i in np.arange(num_domains)]
    for dans in dans_list:
        for session in dans:
            domain_id = int(session["domain"][-2:])
            agent_id = int(str(session["agent"]).split("_")[1])
            is_b = (agent_id % 2) == 0
            if is_b:
                agent = "Agent_A"
            else:
                agent = "Agent_B"
            # Add the number of offers
            dans_totals[domain_id][agent]["num_offers"] += float(session["num_offers"])
            # "fortunate_%" "selfish_%" "concession_%" "unfortunate_%" "nice_%" "silent_%" "behav_sens" "pref_sens"
            # Add the percentage of fortunate moves
            dans_totals[domain_id][agent]["fortunate_%"] += float(session["fortunate_%"])
            # Add the percentage of selfish moves
            dans_totals[domain_id][agent]["selfish_%"] += float(session["selfish_%"])
            # Add the percentage of concession moves
            dans_totals[domain_id][agent]["concession_%"] += float(session["concession_%"])
            # Add the percentage of unfortunate moves
            dans_totals[domain_id][agent]["unfortunate_%"] += float(session["unfortunate_%"])
            # Add the percentage of unfortunate moves
            dans_totals[domain_id][agent]["nice_%"] += float(session["nice_%"])
            # Add the percentage of silent moves
            dans_totals[domain_id][agent]["silent_%"] += float(session["silent_%"])
            # Cannot add the sensitivity to the opponent's behaviour, "behav_sens", because it may be infinite
            # Add the sensitivity to the opponent's preferences
            dans_totals[domain_id][agent]["pref_sens"] += float(session["pref_sens"])

    # Generate a dictionary that represents the aggregation of the Dans metrics
    dans_aggregate = defaultdict(lambda: [])
    dans = dans_list[0]
    for domain_id in range(num_domains):
        for agent in ["Agent_A", "Agent_B"]:
            # Domain
            dans_aggregate["domain_id"].append(domain_id)
            # Agent
            dans_aggregate["agent"].append(agent)
            # Total Number of Offers
            total_num_offers = dans_totals[domain_id][agent]["num_offers"]
            dans_aggregate["num_offers"].append(total_num_offers)
            # Average percentage of fortunate moves
            fortunate = float(dans_totals[domain_id][agent]["fortunate_%"]) / num_tournaments
            dans_aggregate["fortunate_%"].append(fortunate)
            # Average percentage of selfish moves
            selfish = float(dans_totals[domain_id][agent]["selfish_%"]) / num_tournaments
            dans_aggregate["selfish_%"].append(selfish)
            # Average percentage of concession moves
            concession = float(dans_totals[domain_id][agent]["concession_%"]) / num_tournaments
            dans_aggregate["concession_%"].append(concession)
            # Average percentage of unfortunate moves
            unfortunate = float(dans_totals[domain_id][agent]["unfortunate_%"]) / num_tournaments
            dans_aggregate["unfortunate_%"].append(unfortunate)
            # Average percentage of nice moves
            nice = float(dans_totals[domain_id][agent]["nice_%"]) / num_tournaments
            dans_aggregate["nice_%"].append(nice)
            # Average percentage of silent moves
            silent = float(dans_totals[domain_id][agent]["silent_%"]) / num_tournaments
            dans_aggregate["silent_%"].append(silent)
            # Compute average sensitivity to opponent's behaviour
            numerator = fortunate + nice + concession
            denominator = unfortunate + silent + selfish
            if denominator == 0:
                behav_sens = "inf"
            else:
                behav_sens = float(numerator) / float(denominator)
            dans_aggregate["behav_sens"].append(behav_sens)
            # Average sensitivity to opponent's preferences
            pref_sens = float(dans_totals[domain_id][agent]["pref_sens"]) / num_tournaments
            dans_aggregate["pref_sens"].append(pref_sens)

    # Write aggregate of the dans metrics to a csv file
    dans_summary = pd.DataFrame(dans_aggregate)
    dans_summary.to_csv(results_dir.joinpath("dans_evaluation.csv"), index=False)


if __name__ == "__main__":
    main()
