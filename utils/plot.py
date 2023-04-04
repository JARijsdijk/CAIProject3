import json
import os
from pathlib import Path
from collections import defaultdict

import plotly.graph_objects as go
from plotly.graph_objs import Figure

from itertools import product


def plot(results_trace: dict, plot_file: str):
    # Get the names of each party
    parties = []
    for party in results_trace["partyprofiles"]:
        parties.append(party)

    # Get the profiles and domain
    profile_a_filepath = results_trace["partyprofiles"][parties[0]]["profile"][5:]
    profile_b_filepath = results_trace["partyprofiles"][parties[1]]["profile"][5:]
    domain = profile_a_filepath[8:16]

    fig = go.Figure()

    # Plot special points
    plot_specials(domain, fig)

    # Plot all possible bids
    plot_possible_bids(profile_a_filepath, profile_b_filepath, fig)

    # Plot results trace
    plot_dans(results_trace, parties, fig)

    fig.update_layout(
        legend={
            "yanchor": "bottom",
            "y": 1,
            "xanchor": "left",
            "x": 0,
        },
    )
    fig.update_xaxes(title_text="Utility A", range=[0, 1], ticks="outside")
    fig.update_yaxes(title_text="Utility B", range=[0, 1], ticks="outside")
    fig.write_html(f"{os.path.splitext(plot_file)[0]}.html")


def plot_specials(domain: str, fig: Figure):
    # Get special points in the domain from file
    specials_filepath = Path("domains/" + domain + "/specials.json")
    with open(specials_filepath, "r") as f:
        specials = json.load(f)
        pareto_front = specials["pareto_front"]
        kalai = specials["kalai"]
        nash = specials["nash"]

    # Plot pareto front
    plot_pareto_front(pareto_front, fig)

    # Plot kalai
    plot_kalai(kalai, fig)

    # Plot nash point
    plot_nash(nash, fig)


def plot_nash(nash, fig: Figure):
    # Plot nash point
    x, y = nash["utility"]
    text = "<br>".join(
        [f"<b>utility A: {x:.3f}</b>"]
        + [f"<b>utility B: {y:.3f}</b>"]
        + [f"{i}: {v}" for i, v in nash["bid"].items()]
    )
    fig.add_trace(
        go.Scatter(
            x=[x],
            y=[y],
            mode="markers",
            name="Nash",
            legendgroup="Nash",
            marker=dict(color="DarkOrange", size=8, line_width=0, symbol="x"),
            hovertext=text,
            hoverinfo="text",
        )
    )


def plot_kalai(kalai, fig: Figure):
    # Plot kalai
    x, y = kalai["utility"]
    text = "<br>".join(
        [f"<b>utility A: {x:.3f}</b>"]
        + [f"<b>utility B: {y:.3f}</b>"]
        + [f"{i}: {v}" for i, v in kalai["bid"].items()]
    )
    fig.add_trace(
        go.Scatter(
            x=[x],
            y=[y],
            mode="markers",
            name="Kalai-Smorodinsky",
            legendgroup="Kalai",
            marker=dict(color="DarkCyan", size=8, line_width=0, symbol="cross"),
            hovertext=text,
            hoverinfo="text",
        )
    )


def plot_pareto_front(pareto_front, fig: Figure):
    # Plot pareto front
    xs = []
    ys = []
    texts = []
    for item in pareto_front:
        bid = item["bid"]
        x, y = item["utility"]
        xs.append(x)
        ys.append(y)
        texts.append("<br>".join(
            [f"<b>utility A: {x:.3f}</b>"]
            + [f"<b>utility B: {y:.3f}</b>"]
            + [f"{i}: {v}" for i, v in bid.items()]
        ))
    fig.add_trace(
        go.Scatter(
            x=xs,
            y=ys,
            mode="lines+markers",
            name="Pareto",
            legendgroup="Pareto",
            marker=dict(color="DarkGreen", size=3),
            line=dict(color="DarkGreen", width=1.5),
            hovertext=texts,
            hoverinfo="text",
        )
    )


def plot_possible_bids(profile_a_filepath, profile_b_filepath, fig: Figure):
    # Get the bidding space of the domain
    # By getting the issues and values in the profile of party A
    with open(profile_a_filepath, "r") as f:
        profile_a = json.load(f)
        issue_weights_a = profile_a["LinearAdditiveUtilitySpace"]["issueWeights"]
        issues = issue_weights_a.keys()
        issue_values_a = defaultdict(lambda: [])
        for issue in issues:
            issue_value = profile_a["LinearAdditiveUtilitySpace"]["issueUtilities"][issue]["DiscreteValueSetUtilities"][
                "valueUtilities"]
            for value_id, value in issue_value.items():
                issue_values_a[issue].append((value_id, value))
        cartesian_product_a = [dict(zip(issue_values_a, v)) for v in product(*issue_values_a.values())]

    # And by getting the issues and values in the profile of party B
    with open(profile_b_filepath, "r") as f:
        profile_b = json.load(f)
        issue_weights_b = profile_b["LinearAdditiveUtilitySpace"]["issueWeights"]
        issue_values_b = defaultdict(lambda: [])
        for issue in issues:
            issue_value = profile_b["LinearAdditiveUtilitySpace"]["issueUtilities"][issue]["DiscreteValueSetUtilities"][
                "valueUtilities"]
            for value_id, value in issue_value.items():
                issue_values_b[issue].append((value_id, value))
        cartesian_product_b = [dict(zip(issue_values_b, v)) for v in product(*issue_values_b.values())]

    # Then for each combination we plot a point
    # where each point needs:
    #   a text giving the value ids,
    #   a float for the utility of party A, and
    #   a float for the utility of party B
    xs = []
    ys = []
    texts = []
    for i, x in enumerate(cartesian_product_a):
        bid = defaultdict(lambda: "")
        utility_a = 0
        utility_b = 0
        for issue, value_tuple in x.items():
            value_id = value_tuple[0]
            value_a = value_tuple[1]
            value_b = cartesian_product_b[i][issue][1]
            bid[issue] = value_id
            utility_a += issue_weights_a[issue] * value_a
            utility_b += issue_weights_b[issue] * value_b
        xs.append(utility_a)
        ys.append(utility_b)
        texts.append("<br>".join(
            [f"<b>utility A: {utility_a:.3f}</b>"]
            + [f"<b>utility B: {utility_b:.3f}</b>"]
            + [f"{i}: {v}" for i, v in bid.items()]
        ))

    fig.add_trace(
        go.Scatter(
            x=xs,
            y=ys,
            mode="markers",
            name="All Possible Bids",
            legendgroup="Bidspace",
            marker=dict(color="Grey"),
            hovertext=texts,
            hoverinfo="text",
        )
    )


def plot_dans(results_trace: dict, parties, fig: Figure):
    xs = defaultdict(lambda: [])
    ys = defaultdict(lambda: [])
    texts = defaultdict(lambda: [])
    accepted = False
    accepted_x = []
    accepted_y = []
    accepted_text = []
    for action in results_trace["actions"]:
        if "Offer" in action:
            offer = action["Offer"]
            party = offer["actor"]
            utilities = []
            for agent, utility in offer["utilities"].items():
                utilities.append(utility)
            x = utilities[0]
            y = utilities[1]
            bid = offer["bid"]["issuevalues"]
            text = "<br>".join(
                [f"<b>utility A: {x:.3f}</b>"]
                + [f"<b>utility B: {y:.3f}</b>"]
                + [f"{i}: {v}" for i, v in bid.items()]
            )
            xs[party].append(x)
            ys[party].append(y)
            texts[party].append(text)
        elif "Accept" in action:
            accepted = True
            offer = action["Accept"]
            party = offer["actor"]
            utilities = []
            for agent, utility in offer["utilities"].items():
                utilities.append(utility)
            accepted_x = utilities[0]
            accepted_y = utilities[1]
            bid = offer["bid"]["issuevalues"]
            name = "_".join(party.split("_")[-2:])
            accepted_text = "<br>".join(
                [f"Accepted by {name}:"]
                + [f"<b>utility A: {accepted_x:.3f}</b>"]
                + [f"<b>utility B: {accepted_y:.3f}</b>"]
                + [f"{i}: {v}" for i, v in bid.items()]
            )

    # Plot offers
    color = {0: "red", 1: "blue"}
    for i, party in enumerate(parties):
        name = "_".join(party.split("_")[-2:])
        fig.add_trace(
            go.Scatter(
                mode="lines+markers",
                x=xs[party],
                y=ys[party],
                name=f"{name} offered - lines",
                legendgroup=party.join(" - lines"),
                marker={"color": color[i]},
                hovertext=texts[party],
                hoverinfo="text",
            )
        )
        fig.add_trace(
            go.Scatter(
                mode="markers",
                x=xs[party],
                y=ys[party],
                name=f"{name} offered",
                legendgroup=party,
                marker={"color": color[i]},
                hovertext=texts[party],
                hoverinfo="text",
            )
        )

    # Plot acceptance point if it exists
    if accepted:
        fig.add_trace(
            go.Scatter(
                mode="markers",
                x=[accepted_x],
                y=[accepted_y],
                name="agreement",
                marker={"color": "DarkMagenta"},
                hovertext=[accepted_text],
                hoverinfo="text",
            )
        )
