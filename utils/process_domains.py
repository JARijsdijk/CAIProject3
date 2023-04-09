import json
import csv
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd


def main():
    # Get all domain directories in the domains directory
    domains_dir = Path("../domains/")
    domain_dir_list: [Path] = [f for f in domains_dir.iterdir() if f.is_dir()]

    domain_info = defaultdict(lambda: [])
    for domain_id, domain_dir in enumerate(domain_dir_list):
        specials_csv_file = domain_dir.joinpath("specials.json")
        specials = json.load(open(specials_csv_file))
        # Domain ID
        domain_info["domain_id"].append(domain_id)
        # Size - number of bids in bidding space
        size = specials["size"]
        domain_info["size"].append(size)
        # Nash utilities
        nash = specials["nash"]["utility"]
        domain_info["nash_a"].append(nash[0])
        domain_info["nash_b"].append(nash[1])
        # Kalai utilities
        kalai = specials["kalai"]["utility"]
        domain_info["kalai_a"].append(kalai[0])
        domain_info["kalai_b"].append(kalai[1])

    # Write domain info to a csv file
    domains_summary = pd.DataFrame(domain_info)
    domains_summary.to_csv(domains_dir.joinpath("domains_summary.csv"), index=False)


if __name__ == "__main__":
    main()
