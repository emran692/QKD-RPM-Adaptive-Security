from pathlib import Path
import matplotlib.pyplot as plt

output_dir = Path("results/figures")
output_dir.mkdir(parents=True, exist_ok=True)
output_file = output_dir / "Figure_4_7_Short_Interval_Fallback_Timeline.png"

start, end = 220, 230
hybrid_time, v5_time = 229, 234

fig, ax = plt.subplots(figsize=(11, 5.8))

# Degradation interval
ax.axvspan(start, end, alpha=0.18, label="Degradation interval (220–230 s)")
ax.axvline(start, linestyle="--", linewidth=1)
ax.axvline(end, linestyle="--", linewidth=1)

# Controller event markers
ax.scatter(hybrid_time, 1, s=120, marker="o", zorder=3,
           label="Hybrid: timely fallback")
ax.scatter(v5_time, 0, s=120, marker="s", zorder=3,
           label="V5: late fallback")

# Event annotations
ax.annotate(
    "Hybrid: 229 s\nTIMELY\nISOLATION_FOREST_PERSISTENT_ANOMALY",
    xy=(hybrid_time, 1), xytext=(218.5, 1.28),
    arrowprops=dict(arrowstyle="->", linewidth=1),
    fontsize=8, ha="left"
)

ax.annotate(
    "V5: 234 s\nLATE\nROLLING_QBER_HIGH",
    xy=(v5_time, 0), xytext=(231, -0.35),
    arrowprops=dict(arrowstyle="->", linewidth=1),
    fontsize=8, ha="left"
)

ax.set_yticks([0, 1])
ax.set_yticklabels(["V5 baseline", "Hybrid IF-Persistence"])
ax.set_xlim(218, 237)
ax.set_ylim(-0.65, 1.65)
ax.set_xlabel("Time (seconds)")
ax.set_title(
    "Fallback Detection Timeline: Short Degradation Interval, Seed 1003",
    fontweight="bold"
)

ax.grid(axis="x", alpha=0.25)
ax.legend(loc="upper right", fontsize=8)
ax.text(
    0.5, -0.20,
    "Hybrid fallback occurred 5 seconds earlier in this observed interval. "
    "This is a single-seed case study, not an aggregate performance estimate.",
    transform=ax.transAxes, ha="center", fontsize=8, wrap=True
)

plt.tight_layout()
fig.savefig(output_file, dpi=300, bbox_inches="tight")
plt.close(fig)

print("FIGURE 4.7 GENERATED")
print(f"Output: {output_file}")
print("Degradation interval: 220–230 seconds")
print("Hybrid fallback: 229 seconds (TIMELY)")
print("V5 fallback: 234 seconds (LATE)")
print("Observed timing difference: 5 seconds")
