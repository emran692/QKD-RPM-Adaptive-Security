
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

OUTPUT_DIR = Path("results/figures")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = OUTPUT_DIR / "Figure_1_1_Conceptual_Framework_Overview.png"

fig, ax = plt.subplots(figsize=(16, 9))
ax.set_xlim(0, 16)
ax.set_ylim(0, 10)
ax.axis("off")


def add_box(x, y, width, height, title, subtitle=""):
    box = FancyBboxPatch(
        (x, y), width, height,
        boxstyle="round,pad=0.04,rounding_size=0.15",
        linewidth=1.6,
        edgecolor="#26364A",
        facecolor="#EAF1F8"
    )
    ax.add_patch(box)

    label = title if not subtitle else f"{title}\n{subtitle}"
    ax.text(
        x + width / 2,
        y + height / 2,
        label,
        ha="center",
        va="center",
        fontsize=9,
        fontweight="bold",
        color="#172B4D",
        wrap=True
    )


def add_arrow(start, end):
    ax.add_patch(
        FancyArrowPatch(
            start, end,
            arrowstyle="-|>",
            mutation_scale=16,
            linewidth=1.5,
            color="#34495E"
        )
    )



# Data and healthcare context
add_box(
    0.7, 7.6, 4.2, 1.2,
    "Remote Patient Monitoring",
    "Connected medical devices\nand remote monitoring"
)

add_box(
    5.9, 7.6, 4.2, 1.2,
    "Physiological Data",
    "PPG, ECG and other\nphysiological measurements"
)

add_box(
    11.1, 7.6, 4.2, 1.2,
    "Communication Channel",
    "Transfer of monitoring data\nto healthcare platforms"
)


# Security challenge

add_box(
    3.0, 5.3, 4.5, 1.2,
    "Security and Privacy\nRequirements",
    "Confidentiality, integrity\nand secure key management"
)


add_box(
    8.5, 5.3, 4.5, 1.2,
    "Changing Channel Conditions",
    "Variable QBER and simulated key availability"
)

# Proposed framework
add_box(
    4.0, 2.9, 8.0, 1.3,
    "Proposed Adaptive QKD–PQC Framework",
    "Hybrid anomaly detection and adaptive security-mode selection"
)

# Security modes
add_box(
    0.8, 0.6, 6.0, 1.2,
    "QKD Operating Mode",
    "Simulated QKD channel and key-pool management"
)

add_box(
    9.2, 0.6, 6.0, 1.2,
    "Abstract PQC Fallback Mode",
    "Simulated alternative security mode and recovery"
)

# Main data flow
add_arrow((4.9, 8.2), (5.9, 8.2))
add_arrow((10.1, 8.2), (11.1, 8.2))

# Context to security requirements
add_arrow((8.0, 7.6), (5.3, 6.5))
add_arrow((13.0, 7.6), (10.8, 6.5))

# Requirements to proposed framework
add_arrow((5.3, 5.3), (6.5, 4.2))
add_arrow((10.8, 5.3), (9.5, 4.2))

# Adaptive framework to security modes
add_arrow((6.0, 2.9), (3.8, 1.8))
add_arrow((10.0, 2.9), (12.2, 1.8))

# Heading
ax.text(
    8, 9.45,
    "Conceptual Overview of the Proposed Framework",
    ha="center",
    va="center",
    fontsize=15,
    fontweight="bold",
    color="#172B4D"
)

# Scope note
ax.text(
    8, 0.15,
    "Conceptual representation of the software-based simulation; "
    "not a physical QKD deployment.",
    ha="center",
    va="center",
    fontsize=8,
    color="#555555"
)

plt.savefig(OUTPUT_FILE, dpi=300, bbox_inches="tight")
plt.close()

print("FIGURE 1.1 GENERATED")
print(f"Output: {OUTPUT_FILE}")
