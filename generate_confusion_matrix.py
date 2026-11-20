from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.metrics import confusion_matrix, accuracy_score, precision_score, recall_score, f1_score

# Input and output paths
input_file = Path("results/anomaly_detection_v5_hybrid_confirmation/isolation_forest_v5_predictions.csv")
output_dir = Path("results/figures")
output_dir.mkdir(parents=True, exist_ok=True)

# Load predictions
df = pd.read_csv(input_file)

# Select only the temporal evaluation period
df["time_seconds"] = pd.to_numeric(df["time_seconds"])
df["anomaly_prediction"] = pd.to_numeric(df["anomaly_prediction"])

evaluation = df[
    (df["time_seconds"] >= 220) &
    (df["time_seconds"] <= 507)
].copy()

# Actual labels: NORMAL=0, DEGRADED=1
actual = (evaluation["channel_status"] == "DEGRADED").astype(int)
predicted = evaluation["anomaly_prediction"].astype(int)

# Calculate confusion matrix
cm = confusion_matrix(actual, predicted, labels=[0, 1])
tn, fp, fn, tp = cm.ravel()

accuracy = accuracy_score(actual, predicted)
precision = precision_score(actual, predicted, zero_division=0)
recall = recall_score(actual, predicted, zero_division=0)
f1 = f1_score(actual, predicted, zero_division=0)

# Verify against the independently checked values
expected = (214, 14, 0, 60)
calculated = (tn, fp, fn, tp)

if calculated != expected:
    raise ValueError(
        f"Metric mismatch! Expected {expected}, calculated {calculated}"
    )

# Create figure
fig, ax = plt.subplots(figsize=(8, 6))
image = ax.imshow(cm, cmap="Blues")

ax.set_title(
    "Confusion Matrix – Hybrid Isolation Forest",
    fontsize=14,
    fontweight="bold",
    pad=16
)
ax.set_xlabel("Predicted Class", fontsize=11)
ax.set_ylabel("Actual Class", fontsize=11)

ax.set_xticks([0, 1])
ax.set_xticklabels(["NORMAL", "DEGRADED"])
ax.set_yticks([0, 1])
ax.set_yticklabels(["NORMAL", "DEGRADED"])

# Annotate cell counts
threshold = cm.max() / 2
for i in range(2):
    for j in range(2):
        ax.text(
            j, i, f"{cm[i, j]}",
            ha="center",
            va="center",
            fontsize=18,
            fontweight="bold",
            color="white" if cm[i, j] > threshold else "black"
        )

fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)

metrics_text = (
    f"Accuracy: {accuracy*100:.2f}%   "
    f"Precision: {precision*100:.2f}%   "
    f"Recall: {recall*100:.2f}%   "
    f"F1-score: {f1*100:.2f}%"
)

fig.text(0.5, 0.025, metrics_text, ha="center", fontsize=9)
fig.text(
    0.5, 0.075,
    "Evaluation period: 220–507 seconds | 288 observations",
    ha="center",
    fontsize=9
)

plt.tight_layout(rect=[0, 0.12, 1, 1])

output_file = output_dir / "Figure_4_1_Confusion_Matrix.png"
fig.savefig(output_file, dpi=300, bbox_inches="tight")
plt.close(fig)

print("\n========== FIGURE GENERATED ==========")
print(f"Evaluation samples : {len(evaluation)}")
print(f"TN: {tn} | FP: {fp} | FN: {fn} | TP: {tp}")
print(f"Accuracy           : {accuracy*100:.2f}%")
print(f"Precision          : {precision*100:.2f}%")
print(f"Recall             : {recall*100:.2f}%")
print(f"F1-score           : {f1*100:.2f}%")
print(f"\nSaved: {output_file}")
print("Verification: PASSED")
