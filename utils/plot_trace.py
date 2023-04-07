import os
from collections import defaultdict

import plotly.graph_objects as go


def plot_trace(results_trace: dict, plot_file: str):
    utilities = defaultdict(lambda: defaultdict(lambda: {"x": [], "y": [], "bids": []}))
    accept = {"x": [], "y": [], "bids": []}
    for index, action in enumerate(results_trace["actions"], 1):
        if "Offer" in action:
            offer = action["Offer"]
            actor = offer["actor"]
            for agent, util in offer["utilities"].items():
                utilities[agent][actor]["x"].append(index)
                utilities[agent][actor]["y"].append(util)
                utilities[agent][actor]["bids"].append(offer["bid"]["issuevalues"])
        elif "Accept" in action:
            offer = action["Accept"]
            index -= 1
            for agent, util in offer["utilities"].items():
                accept["x"].append(index)
                accept["y"].append(util)
                accept["bids"].append(offer["bid"]["issuevalues"])

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            mode="markers",
            x=accept["x"],
            y=accept["y"],
            name="agreement",
            marker={"color": "DarkMagenta", "size": 15},
            hoverinfo="skip",
        )
    )

    color = {0: "red", 1: "blue"}
    for i, (agent, data) in enumerate(utilities.items()):
        for actor, utility in data.items():
            name = "_".join(agent.split("_")[-2:])
            text = []
            for bid, util in zip(utility["bids"], utility["y"]):
                text.append(
                    "<br>".join(
                        [f"<b>utility: {util:.3f}</b><br>"]
                        + [f"{i}: {v}" for i, v in bid.items()]
                    )
                )
            fig.add_trace(
                go.Scatter(
                    mode="lines+markers" if agent == actor else "markers",
                    x=utilities[agent][actor]["x"],
                    y=utilities[agent][actor]["y"],
                    name=f"{name} offered" if agent == actor else f"{name} received",
                    legendgroup=agent,
                    marker={"color": color[i]},
                    hovertext=text,
                    hoverinfo="text",
                )
            )

    fig.update_layout(
        height=1500,
        width=1500,
        legend={
            "yanchor": "bottom",
            "y": 1,
            "xanchor": "left",
            "x": 0,
            "orientation": "h",
        },
    )
    fig.update_xaxes(title_text="Round", range=[0, len(results_trace["actions"]) + 10], ticks="outside")
    fig.update_yaxes(title_text="Utility", range=[0, 1 + 0.1], ticks="outside")
    fig.write_html(f"{os.path.splitext(plot_file)[0]}.html")
