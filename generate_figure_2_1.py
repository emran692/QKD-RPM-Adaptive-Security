
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

OUTPUT_DIR = Path("results/figures")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = OUTPUT_DIR / "Figure_2_1_Research_Gap_and_Proposed_Direction.png"

fig, ax = plt.subplots(figsize=(16, 10))
ax.set_xlim(0, 16)
ax.set_ylim(0, 11)
ax.axis("off")


def add_box(x, y, width, height, title, subtitle="",
            facecolor="#EAF1F8"):
    box = FancyBboxPatch(
        (x, y), width, height,
        boxstyle="round,pad=0.04,rounding_size=0.15",
        linewidth=1.5,
        edgecolor="#26364A",
        facecolor=facecolor
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


# Literature research areas
add_box(
    0.5, 8.0, 4.5, 1.3,
    "QKD-Based Healthcare Security",
    "Quantum key distribution and\nsecure communication research"
)

add_box(
    5.75, 8.0, 4.5, 1.3,
    "PQC-Based Security",
    "Post-quantum cryptography and\nquantum-resistant protection"
)

add_box(
    11.0, 8.0, 4.5, 1.3,
    "Healthcare IoT Security",
    "Authentication, privacy and\nconnected healthcare protection"
)

# Identified research challenges
add_box(
    1.0, 5.5, 6.0, 1.4,
    "Research Challenges",
    "Limited integration of adaptive security,\nkey-pool management and channel monitoring"
)

add_box(
    9.0, 5.5, 6.0, 1.4,
    "Research Motivation",
    "Changing channel conditions and\ncontinuous RPM communication requirements"
)

# Research gap
add_box(
    3.0, 3.0, 10.0, 1.4,
    "Identified Research Gap",
    "Need for a simulation-based framework combining\nadaptive QKD–PQC mode selection and hybrid detection",
    facecolor="#F5EEDC"
)

# Proposed direction
add_box(
    3.0, 0.6, 10.0, 1.4,
    "Proposed Research Direction",
    "Simulated QKD, abstract PQC fallback, hybrid anomaly detection\nand simulated key-pool management",
    facecolor="#E5F2E9"
)

# Arrows from research areas to challenges
add_arrow((2.75, 8.0), (3.8, 6.9))
add_arrow((8.0, 8.0), (8.0, 6.9))
add_arrow((13.25, 8.0), (12.2, 6.9))

# Challenges to research gap
add_arrow((4.0, 5.5), (6.0, 4.4))
add_arrow((12.0, 5.5), (10.0, 4.4))

# Research gap to proposed direction
add_arrow((8.0, 3.0), (8.0, 2.0))

# Heading
ax.text(
    8, 10.3,
    "Research Gap and Proposed Research Direction",
    ha="center",
    va="center",
    fontsize=15,
    fontweight="bold",
    color="#172B4D"
)

# Scope note
ax.text(
    8, 0.2,
    "Conceptual synthesis of the reviewed literature and project scope.",
    ha="center",
    va="center",
    fontsize=8,
    color="#555555"
)

plt.savefig(OUTPUT_FILE, dpi=300, bbox_inches="tight")
plt.close()

print("FIGURE 2.1 GENERATED")
print(f"Output: {OUTPUT_FILE}")
