
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

# Output directory
OUTPUT_DIR = Path("results/figures")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Figure setup
fig, ax = plt.subplots(figsize=(18, 11))
ax.set_xlim(0, 18)
ax.set_ylim(0, 11)
ax.axis("off")

# Colors
navy = "#17365D"
blue = "#DCEAF7"
green = "#E2F0D9"
orange = "#FCE4D6"
purple = "#E4DFEC"
grey = "#F2F2F2"
dark = "#222222"


def draw_box(x, y, width, height, title, subtitle="",
             facecolor=blue, edgecolor=navy, fontsize=10):
    box = FancyBboxPatch(
        (x, y),
        width,
        height,
        boxstyle="round,pad=0.12,rounding_size=0.15",
        linewidth=1.5,
        edgecolor=edgecolor,
        facecolor=facecolor
    )
    ax.add_patch(box)

    ax.text(
        x + width / 2,
        y + height * 0.65,
        title,
        ha="center",
        va="center",
        fontsize=fontsize,
        fontweight="bold",
        color=dark
    )

    if subtitle:
        ax.text(
            x + width / 2,
            y + height * 0.30,
            subtitle,
            ha="center",
            va="center",
            fontsize=fontsize - 1.5,
            color=dark,
            wrap=True
        )


def arrow(start, end, label=None, color=navy,
          style="-", rad=0.0, label_offset=(0, 0)):
    connection = FancyArrowPatch(
        start,
        end,
        arrowstyle="-|>",
        mutation_scale=15,
        linewidth=1.5,
        color=color,
        linestyle=style,
        connectionstyle=f"arc3,rad={rad}"
    )
    ax.add_patch(connection)

    if label:
        mid_x = (start[0] + end[0]) / 2 + label_offset[0]
        mid_y = (start[1] + end[1]) / 2 + label_offset[1]
        ax.text(
            mid_x, mid_y, label,
            ha="center", va="center",
            fontsize=8, color=color,
            bbox=dict(facecolor="white", edgecolor="none", alpha=0.85)
        )


# Main title
ax.text(
    9, 10.55,
    "Overall Architecture of the Proposed Adaptive QKD-PQC RPM Framework",
    ha="center", va="center",
    fontsize=15, fontweight="bold", color=navy
)

# Left: RPM data preparation
draw_box(
    0.5, 7.9, 3.2, 1.15,
    "PhysioNet PTT Dataset",
    "Selected recording: s1_sit.csv",
    facecolor=grey
)

draw_box(
    0.5, 6.1, 3.2, 1.15,
    "Data Preprocessing",
    "process_physionet.py",
    facecolor=blue
)

draw_box(
    0.5, 4.3, 3.2, 1.15,
    "RPM Traffic Generation",
    "2,040 software-generated packet records",
    facecolor=blue
)

arrow((2.1, 7.9), (2.1, 7.25))
arrow((2.1, 6.1), (2.1, 5.45))

# Center: Simulated channel
draw_box(
    5.0, 7.9, 3.4, 1.15,
    "Simulated QKD Channel",
    "Simulated QBER and key generation rate",
    facecolor=purple
)

draw_box(
    5.0, 5.9, 3.4, 1.25,
    "Hybrid Anomaly Detection",
    "Isolation Forest + persistence confirmation",
    facecolor=orange
)

arrow((6.7, 7.9), (6.7, 7.15), "Channel observations")

# Controller
draw_box(
    9.8, 5.9, 3.2, 1.25,
    "Adaptive Security Controller",
    "Monitoring and mode-selection logic",
    facecolor=green
)

arrow((8.4, 6.52), (9.8, 6.52), "Detection output")

# Operating modes
draw_box(
    14.1, 7.5, 3.1, 1.15,
    "QKD Operating Mode",
    "Simulated QKD operation",
    facecolor=blue
)

draw_box(
    14.1, 5.2, 3.1, 1.15,
    "PQC Fallback Mode",
    "Abstract software simulation",
    facecolor=orange
)

arrow((13.0, 6.8), (14.1, 7.95), "Normal operation")
arrow((13.0, 6.2), (14.1, 5.75), "Fallback condition")

# Recovery feedback
arrow(
    (15.65, 5.2),
    (15.65, 7.5),
    "Recovery condition",
    color="darkgreen",
    rad=-0.18,
    label_offset=(0.65, 0)
)

# Key pool
draw_box(
    9.8, 3.6, 3.2, 1.15,
    "Key-Pool Management",
    "Generation, consumption, replenishment",
    facecolor=purple
)

arrow((14.8, 7.5), (11.4, 4.75), "QKD key events", rad=0.10)

# Event logging
draw_box(
    5.0, 1.5, 8.0, 1.15,
    "Monitoring and Performance Evaluation",
    "Detection results, mode transitions, key-pool records and metrics",
    facecolor=grey
)

arrow((6.7, 5.9), (7.0, 2.65), "Detection logs", rad=0.08)
arrow((11.4, 3.6), (10.5, 2.65), "Pool records")
arrow((15.65, 5.2), (12.5, 2.65), "Mode events", rad=-0.08)

# RPM workload connection (conceptual)
arrow(
    (3.7, 4.85),
    (5.0, 8.15),
    "RPM workload context",
    color="dimgray",
    style="--",
    rad=-0.15,
    label_offset=(-0.25, 0.25)
)

# Independent AES branch
draw_box(
    0.5, 1.5, 3.2, 1.15,
    "Separate AES-256-GCM Test",
    "Independent random 256-bit placeholder keys",
    facecolor=orange
)

ax.text(
    2.1, 1.0,
    "Not integrated with adaptive QKD-PQC controller",
    ha="center", va="center",
    fontsize=8, color="firebrick", fontstyle="italic"
)

# Footer
ax.text(
    9, 0.35,
    "Software-based simulation | No physical QKD or standardized PQC implementation",
    ha="center", va="center",
    fontsize=9, color="dimgray"
)

plt.tight_layout()

output_file = OUTPUT_DIR / "Figure_3_1_System_Architecture.png"

plt.savefig(
    output_file,
    dpi=300,
    bbox_inches="tight",
    facecolor="white"
)

plt.close(fig)

print("FIGURE 3.1 GENERATED")
print(f"Output: {output_file}")
