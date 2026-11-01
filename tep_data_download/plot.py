
import matplotlib.pyplot as plt
import pandas as pd

def plot(
    df: pd.DataFrame,
    rows: list[list[str]],
    *,
    figsize: tuple[float, float] | None = None,
    sharex: bool = True,
    linewidth: float = 2,
    grid_alpha: float = 0.3,
):
    """
    Plot groups of DataFrame columns on stacked axes.

    Each inner list in `rows` defines the columns plotted on one axis.

    Example
    -------
    plot(
        df,
        [
            ["respiration"],
            ["respiration_amplitude"],
            ["respiration_period", "respiration_previous_period"],
        ],
    )
    """
    if not rows:
        raise ValueError("rows must contain at least one list of column names")

    missing = [
        column
        for columns in rows
        for column in columns
        if column not in df.columns
    ]
    if missing:
        raise KeyError(f"Columns not found in DataFrame: {missing}")

    nrows = len(rows)

    if figsize is None:
        figsize = (16, max(3, 2.2 * nrows))

    fig, axes = plt.subplots(
        nrows=nrows,
        ncols=1,
        figsize=figsize,
        sharex=sharex,
        constrained_layout=True,
        squeeze=False,
    )

    axes = axes[:, 0]

    for ax, columns in zip(axes, rows):
        for column in columns:
            ax.plot(
                df.index,
                df[column],
                label=column,
                linewidth=linewidth,
            )

        ax.legend(loc="upper right")
        ax.set_ylabel("\n".join(columns))
        ax.grid(alpha=grid_alpha)

    axes[-1].set_xlabel(df.index.name or "Time")

    return fig, axes


def plot_annotated_oscillation(
    df,
    summarydf,
    signal,
    oscillation_id,
    smoothed_signal=None,
    title=None,
):
    """
    Plot one oscillation object with its intrinsic measurements annotated.

    Parameters
    ----------
    df : pandas.DataFrame
        Sample-level DataFrame.
    summarydf : pandas.DataFrame
        One-row-per-oscillation object table.
    signal : str
        Name of the observed signal column.
    oscillation_id : int
        Oscillation object to plot.
    smoothed_signal : str, optional
        Smoothed signal column used for construction.
    title : str, optional
        Plot title.
    """
    row = summarydf.loc[
        summarydf["oscillation_id"] == oscillation_id
    ].iloc[0]

    start_index = int(row["start_index"])
    peak_index = int(row["peak_index"])
    end_index = int(row["end_index"])

    y_column = smoothed_signal or signal
    segment = df.loc[start_index:end_index]

    start_value = df.loc[start_index, y_column]
    peak_value = df.loc[peak_index, y_column]
    end_value = df.loc[end_index, y_column]

    baseline = (start_value + end_value) / 2
    amplitude = row["amplitude"]

    fig, ax = plt.subplots(figsize=(8, 4.5))

    if smoothed_signal is not None:
        ax.plot(
            segment.index,
            segment[signal],
            linewidth=1,
            alpha=0.45,
            label="Observed signal",
        )

    ax.plot(
        segment.index,
        segment[y_column],
        linewidth=2,
        label="Oscillation signal",
    )

    ax.axvspan(
        start_index,
        peak_index,
        alpha=0.10,
        label="Rising phase",
    )

    ax.axvspan(
        peak_index,
        end_index,
        alpha=0.10,
        label="Falling phase",
    )

    ax.scatter(
        [start_index, peak_index, end_index],
        [start_value, peak_value, end_value],
        s=60,
        zorder=3,
    )

    ax.vlines(
        peak_index,
        baseline,
        peak_value,
        linewidth=1.5,
    )

    ax.annotate(
        f"Amplitude = {amplitude:.3f}",
        xy=(peak_index, (baseline + peak_value) / 2),
        xytext=(8, 0),
        textcoords="offset points",
        va="center",
    )

    ax.annotate(
        f"Rise = {row['rise_duration']:.0f}",
        xy=((start_index + peak_index) / 2, start_value),
        xytext=(0, -28),
        textcoords="offset points",
        ha="center",
    )

    ax.annotate(
        f"Fall = {row['fall_duration']:.0f}",
        xy=((peak_index + end_index) / 2, end_value),
        xytext=(0, -28),
        textcoords="offset points",
        ha="center",
    )

    ax.annotate(
        f"Period = {row['period']:.0f}",
        xy=((start_index + end_index) / 2, min(start_value, end_value)),
        xytext=(0, -52),
        textcoords="offset points",
        ha="center",
    )

    ax.text(
        0.02,
        0.95,
        (
            f"O{oscillation_id}\n"
            f"Duration = {row['duration']:.0f}\n"
            f"Symmetry = {row['temporal_symmetry']:.3f}"
        ),
        transform=ax.transAxes,
        va="top",
    )

    ax.set_title(title or f"Oscillation object O{oscillation_id}")
    ax.set_xlabel("Time index")
    ax.set_ylabel(signal)
    ax.grid(alpha=0.3)
    ax.legend(loc="upper right")

    return fig, ax

import matplotlib.pyplot as plt
import pandas as pd


def plot_oscillation_panel(
    ax,
    df,
    summarydf,
    signal,
    object_ids,
    *,
    smoothed_signal=None,
    title=None,
    ylabel=None,
):
    """
    Plot observed data, the construction signal, transition points,
    rising/falling phases, and oscillation-object identifiers.

    Parameters
    ----------
    ax : matplotlib.axes.Axes
        Axis on which to draw the plot.
    df : pandas.DataFrame
        Sample-level DataFrame indexed by time or sample number.
    summarydf : pandas.DataFrame
        One-row-per-oscillation table containing:
        oscillation_id, start_index, peak_index, and end_index.
    signal : str
        Observed signal column.
    object_ids : iterable
        Oscillation IDs to include.
    smoothed_signal : str, optional
        Signal used to construct the oscillations. When omitted, `signal`
        is used for both the observed and construction signals.
    title : str, optional
        Panel title.
    ylabel : str, optional
        Y-axis label.
    """
    objects = (
        summarydf.loc[
            summarydf["oscillation_id"].isin(object_ids),
            [
                "oscillation_id",
                "start_index",
                "peak_index",
                "end_index",
            ],
        ]
        .dropna()
        .sort_values("start_index")
        .copy()
    )

    # Keep only complete oscillation objects.
    objects = objects.loc[
        (objects["start_index"] < objects["peak_index"])
        & (objects["peak_index"] < objects["end_index"])
    ]

    if objects.empty:
        raise ValueError("No complete oscillation objects were selected.")

    start = objects["start_index"].min()
    end = objects["end_index"].max()

    segment = df.loc[start:end]
    construction_signal = smoothed_signal or signal

    # Default matplotlib color cycle, rather than hard-coded colors.
    cycle = plt.rcParams["axes.prop_cycle"].by_key()["color"]
    observed_color = cycle[0]
    construction_color = cycle[1]
    rising_color = cycle[2]
    falling_color = cycle[3]

    # Observed signal.
    ax.plot(
        segment.index,
        segment[signal],
        linewidth=1.0,
        alpha=0.55 if smoothed_signal else 1.0,
        label="Observed signal",
        color=observed_color,
    )

    # Smoothed/construction signal, when different from the observation.
    if smoothed_signal is not None:
        ax.plot(
            segment.index,
            segment[construction_signal],
            linewidth=2.0,
            label="Smoothed signal",
            color=construction_color,
        )

    y = segment[construction_signal]
    y_min = y.min()
    y_max = y.max()
    y_range = y_max - y_min

    label_y = y_min + 0.06 * y_range

    for _, obj in objects.iterrows():
        object_id = int(obj["oscillation_id"])
        start_index = obj["start_index"]
        peak_index = obj["peak_index"]
        end_index = obj["end_index"]

        start_value = df.loc[start_index, construction_signal]
        peak_value = df.loc[peak_index, construction_signal]
        end_value = df.loc[end_index, construction_signal]

        # Rising and falling phases.
        ax.axvspan(
            start_index,
            peak_index,
            alpha=0.08,
            color=rising_color,
        )
        ax.axvspan(
            peak_index,
            end_index,
            alpha=0.08,
            color=falling_color,
        )

        # Boundaries between oscillation objects.
        ax.axvline(
            start_index,
            linestyle="--",
            linewidth=0.8,
            alpha=0.45,
        )

        # Trough: enter rising.
        ax.scatter(
            start_index,
            start_value,
            marker="v",
            s=55,
            color=rising_color,
            zorder=4,
        )

        # Peak: exit rising / enter falling.
        ax.scatter(
            peak_index,
            peak_value,
            marker="^",
            s=55,
            color=falling_color,
            zorder=4,
        )

        # Oscillation-object label.
        midpoint = start_index + (end_index - start_index) / 2

        ax.text(
            midpoint,
            label_y,
            rf"$O_{{{object_id}}}$",
            ha="center",
            va="bottom",
            fontsize=10,
            fontweight="medium",
        )

    # Final boundary.
    ax.axvline(
        objects["end_index"].max(),
        linestyle="--",
        linewidth=0.8,
        alpha=0.45,
    )

    ax.set_title(title or signal)
    ax.set_ylabel(ylabel or signal)
    ax.grid(alpha=0.25)
    ax.margins(x=0.01)


def add_construction_legend(fig):
    """Add one shared legend for both panels."""
    cycle = plt.rcParams["axes.prop_cycle"].by_key()["color"]

    handles = [
        plt.Line2D(
            [],
            [],
            linewidth=1.0,
            color=cycle[0],
            label="Observed signal",
        ),
        plt.Line2D(
            [],
            [],
            linewidth=2.0,
            color=cycle[1],
            label="Smoothed signal",
        ),
        plt.Rectangle(
            (0, 0),
            1,
            1,
            alpha=0.08,
            color=cycle[2],
            label="Rising phase",
        ),
        plt.Rectangle(
            (0, 0),
            1,
            1,
            alpha=0.08,
            color=cycle[3],
            label="Falling phase",
        ),
        plt.Line2D(
            [],
            [],
            linestyle="none",
            marker="v",
            markersize=7,
            color=cycle[2],
            label="enter rising (trough)",
        ),
        plt.Line2D(
            [],
            [],
            linestyle="none",
            marker="^",
            markersize=7,
            color=cycle[3],
            label="exit rising (peak)",
        ),
    ]

    fig.legend(
        handles=handles,
        loc="lower center",
        ncol=3,
        frameon=True,
        bbox_to_anchor=(0.5, -0.01),
    )
