
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

# Output directory
OUTPUT_DIR = Path("results/figures")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = OUTPUT_DIR / "Figure_3_2_Implementation_Workflow.png"

fig, ax = plt.subplots(figsize=(16, 10))
ax.set_xlim(0, 16)
ax.set_ylim(0, 11)
ax.axis("off")

def add_box(x, y, width, height, title, subtitle=""):
    box = FancyBboxPatch(
        (x, y), width, height,
        boxstyle="round,pad=0.04,rounding_size=0.15",
        linewidth=1.5,
        edgecolor="#26364A",
        facecolor="#EAF1F8"
    )
    ax.add_patch(box)

    text = title if not subtitle else f"{title}\n{subtitle}"
    ax.text(
        x + width / 2,
        y + height / 2,
        text,
        ha="center",
        va="center",
        fontsize=9,
        fontweight="semibold",
        color="#172B4D",
        wrap=True
    )

def add_arrow(start, end):
    arrow = FancyArrowPatch(
        start, end,
        arrowstyle="-|>",
        mutation_scale=16,
        linewidth=1.5,
        color="#34495E"
    )
    ax.add_patch(arrow)

# Workflow stages
add_box(5.0, 9.4, 6.0, 0.9,
        "1. Dataset Preparation",
        "PhysioNet PTT recording selection")

add_box(5.0, 7.9, 6.0, 0.9,
        "2. Data Preprocessing",
        "Signal loading, inspection and RPM workload preparation")

add_box(5.0, 6.4, 6.0, 0.9,
        "3. QKD Channel Simulation",
        "Simulated QBER and key generation rate")

add_box(5.0, 4.9, 6.0, 0.9,
        "4. Hybrid Anomaly Detection",
        "Isolation Forest and persistence-based analysis")

add_box(5.0, 3.4, 6.0, 0.9,
        "5. Adaptive Security Controller",
        "Select simulated QKD or abstract PQC fallback mode")

add_box(1.0, 1.5, 5.5, 1.0,
        "6A. QKD Mode",
        "Simulated key-pool consumption and replenishment")

add_box(9.5, 1.5, 5.5, 1.0,
        "6B. PQC Fallback Mode",
        "Abstract fallback and recovery simulation")

add_box(5.0, 0.0, 6.0, 0.9,
        "7. Evaluation and Reporting",
        "Performance metrics, statistical analysis and figures")

# Main vertical flow
add_arrow((8, 9.4), (8, 8.8))
add_arrow((8, 7.9), (8, 7.3))
add_arrow((8, 6.4), (8, 5.8))
add_arrow((8, 4.9), (8, 4.3))

# Controller branches
add_arrow((6.5, 3.4), (3.75, 2.5))
add_arrow((9.5, 3.4), (12.25, 2.5))

# Both modes lead to evaluation
add_arrow((3.75, 1.5), (6.0, 0.9))
add_arrow((12.25, 1.5), (10.0, 0.9))

ax.text(
    8, 10.65,
    "Implementation Workflow of the Proposed Framework",
    ha="center",
    va="center",
    fontsize=15,
    fontweight="bold",
    color="#172B4D"
)

plt.savefig(OUTPUT_FILE, dpi=300, bbox_inches="tight")
plt.close()

print("FIGURE 3.2 GENERATED")
print(f"Output: {OUTPUT_FILE}")
