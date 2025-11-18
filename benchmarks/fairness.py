# Use Jain's Fairness Index to evaluate the fairness of each atomic operation
# This is measuring fairness between core coherence latency

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# csv format is:
# test,from_core,to_core,avg_latency
CSV = "./results/ccbench_summary.csv"
df = pd.read_csv(
    CSV,
    dtype={
        "test": str,
        "from_core": int,
        "to_core": int
    }
)

def calculate_fairness(latencies):
    n = len(latencies)
    sum_latencies = sum(latencies)
    sum_squared_latencies = sum([latency ** 2 for latency in latencies])

    if sum_squared_latencies == 0:
        fairness_index = 1.0  # All latencies are zero, considered perfectly fair
    else:
        fairness_index = (sum_latencies ** 2) / (n * sum_squared_latencies)
    return fairness_index

def benchmark_tests():
    test_fairness = pd.DataFrame(columns=["test", "fairness"])
    df["avg_latency"] = pd.to_numeric(df["avg_latency"], errors="coerce")

    # run jain's fairness on tests
    unique_tests = df["test"].unique()

    for test in unique_tests:
        test_df = df[df["test"] == test]
        latencies = test_df["avg_latency"].values
        fairness_index = calculate_fairness(latencies)

        test_fairness.loc[len(test_fairness)] = [test, fairness_index]
        print(f"Test: {test}, Jain's Fairness Index: {fairness_index:.4f}")

    # visualise fairness
    plt.figure(figsize=(12, 6))  # width=16 inches, height=8 inches
    test_fairness = test_fairness.sort_values("test")
    bars = plt.bar(test_fairness["test"], test_fairness["fairness"])
    plt.ylabel("Fairness Index")
    plt.xlabel("Test Name")
    plt.ylim(0,1)
    plt.xticks(rotation=90, ha="center")
    plt.tight_layout()
    plt.yticks(np.arange(0, 1.1, 0.1))  # 0 to 1 inclusive
    plt.xlim(-0.5, len(test_fairness["test"]) - 0.5)
    plt.title("Fairness of Different Atomic Operations, Over Core Permutations")
    # annotate values inside each bar
    for bar in bars:
        height = bar.get_height()
        plt.text(
            bar.get_x() + bar.get_width() / 2,  # x position: center of the bar
            height / 2,                          # y position: halfway up the bar
            f"{height:.2f}",                     # text
            ha="center",
            va="center",
            rotation=90,
            color="white"                        # good contrast inside bars
        )
    plt.savefig("./figs/core_placement.png")


def benchmark_core_placement():
    # janes fairness over core comms
    from_to_fairness = pd.DataFrame(columns=["from_core", "to_core", "fairness"])
    from_cores = df["from_core"].unique()
    to_cores = df["to_core"].unique()

    for from_core in from_cores:
        for to_core in to_cores:
            rows = df[(df["from_core"] == from_core) & (df["to_core"] == to_core)]
            if rows.empty:
                from_to_fairness.loc[len(from_to_fairness)] = [from_core, to_core, float("nan")]
                continue
            latencies = rows["avg_latency"].values
            fairness = calculate_fairness(latencies)

            from_to_fairness.loc[len(from_to_fairness)] = [from_core, to_core, fairness]
            print(f"From core: {from_core}, to {to_core}, Jain's Fairness Index: {fairness:.4f}")
    
    # visualise fairness
    grid = from_to_fairness.pivot(index="to_core", columns="from_core", values="fairness")

    cell_size = 0.25  # inches per cell
    fig, ax = plt.subplots(figsize=(cell_size * grid.shape[1],
                                    cell_size * grid.shape[0]))
    cax = ax.imshow(grid, cmap="Greens", interpolation="nearest")
    fig.colorbar(cax, label="Fairness Index")

    # annotate values
    if grid.size <= 40:   # 6x6 or smaller, adjust as you like
        for i, to in enumerate(grid.index):
            for j, frm in enumerate(grid.columns):
                val = grid.loc[to, frm]
                ax.text(j, i, f"{val:.2f}", ha="center", va="center", color="white")

    # set ticks at integer positions
    step = 1
    ax.set_xticks(range(0, len(grid.columns), step))
    ax.set_xticklabels([int(x) for x in grid.columns[::step]])

    ax.set_yticks(range(0, len(grid.index), step))
    ax.set_yticklabels([int(y) for y in grid.index[::step]])
    ax.set_xlabel("From Core")
    ax.set_ylabel("To Core")
    ax.tick_params(axis='x', which='both', bottom=True, top=True, labeltop=True, labelbottom=True)
    ax.tick_params(axis='y', which='both', left=True, right=True, labelleft=True, labelright=True)
    ax.set_title("Fairness Between Cores, Over Different Atomic Operations")

    # overlay values in cells
    for i in range(grid.shape[0]):
        for j in range(grid.shape[1]):
            val = grid.iloc[i, j]
            if np.isnan(val):
                continue
            color = "white" if val > 0.5 else "black"
            ax.text(j, i, f"{val:.2f}", ha="center", va="center", color=color, fontsize=6)

    fig.tight_layout()
    plt.savefig("./figs/from_to_fairness.png")


def heatmap_fai_raw():
    for test_name in df["test"].unique():
        fai = df[df["test"] == "FAI"]
        if fai.empty:
            print("No FAI rows found.")
            return

        grid = fai.pivot(index="to_core", columns="from_core", values="avg_latency")

        # use big figure so 64×64 stays readable
        fig, ax = plt.subplots(figsize=(18, 18))

        cax = ax.imshow(grid, cmap="Blues", aspect="equal")
        fig.colorbar(cax, label="Avg Latency")

        # annotate but tiny font; skip NaN
        for i in range(grid.shape[0]):
            for j in range(grid.shape[1]):
                val = grid.iloc[i, j]
                if np.isnan(val):
                    continue
                ax.text(
                    j, i, f"{val:.0f}",
                    ha="center",
                    va="center",
                    color="black",
                    fontsize=4      # critical for 64×64
                )

        ax.set_xticks(range(len(grid.columns)))
        ax.set_yticks(range(len(grid.index)))
        ax.set_xticklabels(grid.columns, fontsize=6)
        ax.set_yticklabels(grid.index, fontsize=6)

        ax.tick_params(axis='x', bottom=True, top=True, labeltop=True, labelbottom=True)
        ax.tick_params(axis='y', left=True, right=True, labelright=True)

        ax.set_xlabel("From Core")
        ax.set_ylabel("To Core")
        ax.set_title("FAI Raw Avg Latency")

        fig.tight_layout()
        plt.savefig(f"./figs/spam/{test_name}_raw_latency.png", dpi=600)
        print(f"{test_name} is done")




benchmark_tests()
print("\n")
benchmark_core_placement()
heatmap_fai_raw()

