import garlic
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
import trio


async def get_metrics(fingerprint: str) -> garlic.RelayWeight:
    client = garlic.Client()
    response = await client.get_weights(lookup=fingerprint)
    return response.relays[0]


def graph_weights(relay: garlic.RelayWeight) -> None:
    middle_prob = relay.middle_probability["1_month"]
    guard_prob = relay.guard_probability["1_month"]
    exit_prob = relay.exit_probability["1_month"]

    middle_prob.denormalise()
    guard_prob.denormalise()
    exit_prob.denormalise()

    x = [middle_prob.first]
    previous = middle_prob.first
    while (current := previous + middle_prob.interval) <= middle_prob.last:
        x.append(current)
        previous = current

    fig, ax = plt.subplots()
    fig.suptitle("Relay Weights (1 Month Period)")

    ax.plot_date(
        x,
        [x * 100 for x in guard_prob.values],
        "o-",
        color="skyblue",
        linewidth=2,
        markersize=4,
        label="Guard Probability",
    )
    ax.plot_date(
        x,
        [x * 100 for x in middle_prob.values],
        "o-",
        color="mediumvioletred",
        linewidth=2,
        markersize=4,
        label="Middle Probability",
    )
    ax.plot_date(
        x,
        [x * 100 for x in exit_prob.values],
        "o-",
        color="darkolivegreen",
        linewidth=2,
        markersize=4,
        label="Exit Probability",
    )

    ax.xaxis.set_major_locator(mdates.DayLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b-%d"))
    plt.xticks(rotation=45)

    ax.grid(linestyle="--")

    plt.xlabel("Timestamp", fontsize=10)
    plt.ylabel("Probability (%)", fontsize=10)
    plt.legend(loc="upper left")
    plt.show()


def main() -> None:
    fingerprint = "730E0D04D90CC0B15F320F6DFD5DD23752AD52E9"
    relay = trio.run(get_metrics, fingerprint)
    graph_weights(relay)


if __name__ == "__main__":
    main()
