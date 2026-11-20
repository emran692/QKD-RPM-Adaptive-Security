
from pathlib import Path
import json

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

# --------------------------------------------------
# PROJECT CONFIGURATION
# --------------------------------------------------

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "dashboard_data"

QKD_FILE = DATA_DIR / "qkd_generation_508s_v3.csv"
COMPARISON_FILE = DATA_DIR / "v5_vs_v5_if_comparison.csv"
METRICS_FILE = DATA_DIR / "isolation_forest_v5_metrics.csv"
AES_FILE = DATA_DIR / "aes_gcm_summary.json"

GITHUB_URL = "https://github.com/emran692/QKD-RPM-Adaptive-Security"

st.set_page_config(
    page_title="Adaptive QKD–PQC Security Framework",
    page_icon="🔐",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --------------------------------------------------
# CUSTOM DESIGN
# --------------------------------------------------

st.markdown("""
<style>
    .stApp {
        background-color: #F6F8FC;
        color: #172B4D;
    }

    [data-testid="stHeader"] {
        background: rgba(246, 248, 252, 0.95);
    }

    [data-testid="stSidebar"] {
        background-color: #FFFFFF;
        border-right: 1px solid #E5EAF2;
    }

    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
        max-width: 1450px;
    }

    .hero {
        background: linear-gradient(115deg, #102A43, #173F5F);
        padding: 30px 34px;
        border-radius: 15px;
        color: white;
        margin-bottom: 22px;
    }

    .hero h1 {
        color: white;
        font-size: 2.15rem;
        margin-bottom: 8px;
        font-weight: 750;
    }

    .hero p {
        color: #DCE8F2;
        font-size: 1rem;
        margin-bottom: 0;
    }

    .section-label {
        color: #087E8B;
        font-weight: 700;
        font-size: 0.78rem;
        letter-spacing: 1.3px;
        text-transform: uppercase;
        margin-bottom: 5px;
    }

    .metric-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 18px 20px;
        min-height: 112px;
        box-shadow: 0 2px 8px rgba(20, 40, 70, 0.035);
    }

    .metric-label {
        color: #64748B;
        font-size: 0.84rem;
        margin-bottom: 8px;
    }

    .metric-value {
        color: #15324B;
        font-size: 1.75rem;
        font-weight: 750;
    }

    .metric-note {
        color: #64748B;
        font-size: 0.78rem;
        margin-top: 4px;
    }

    .info-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 12px;
    }

    .notice {
        background: #EAF3FA;
        border-left: 4px solid #087E8B;
        border-radius: 7px;
        padding: 13px 17px;
        color: #24445E;
        margin: 15px 0 22px 0;
        font-size: 0.91rem;
    }

    .footer {
        border-top: 1px solid #E2E8F0;
        padding-top: 18px;
        margin-top: 35px;
        color: #64748B;
        font-size: 0.82rem;
    }

    div[data-testid="stTabs"] button {
        font-weight: 600;
    }

    a {
        color: #087E8B !important;
        font-weight: 600;
        text-decoration: none;
    }
</style>
""", unsafe_allow_html=True)


# --------------------------------------------------
# DATA LOADING
# --------------------------------------------------

@st.cache_data
def load_csv(path):
    if path.exists():
        return pd.read_csv(path)
    return None


@st.cache_data
def load_json(path):
    if path.exists():
        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)
    return None


qkd = load_csv(QKD_FILE)
comparison = load_csv(COMPARISON_FILE)
anomaly = load_csv(METRICS_FILE)
aes = load_json(AES_FILE)


# --------------------------------------------------
# REUSABLE COMPONENTS
# --------------------------------------------------

def metric_card(label, value, note=""):
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-note">{note}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


def section_heading(label, title, description=None):
    st.markdown(
        f'<div class="section-label">{label}</div>',
        unsafe_allow_html=True
    )
    st.subheader(title)
    if description:
        st.caption(description)


def show_missing(message):
    st.warning(message)


def chart_style(ax, ylabel, xlabel="Time (seconds)"):
    ax.set_xlabel(xlabel, color="#475569")
    ax.set_ylabel(ylabel, color="#475569")
    ax.grid(True, alpha=0.22)
    ax.set_facecolor("#FFFFFF")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#DCE3EC")
    ax.spines["bottom"].set_color("#DCE3EC")
    ax.tick_params(colors="#64748B")


# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------

with st.sidebar:
    st.markdown("## 🔐 QKD–PQC Framework")
    st.caption("Remote Patient Monitoring Security Research")

    st.divider()

    st.markdown("**PROJECT NAVIGATION**")
    st.markdown("Overview")
    st.markdown("QKD simulation")
    st.markdown("Anomaly detection")
    st.markdown("Controller comparison")
    st.markdown("AES-GCM evaluation")

    st.divider()

    st.markdown("**PROJECT REPOSITORY**")
    st.markdown(f"[View on GitHub ↗]({GITHUB_URL})")

    st.divider()

    st.caption("Academic software simulation")
    st.caption("Research prototype | 2026")


# --------------------------------------------------
# HEADER
# --------------------------------------------------

st.markdown("""
<div class="hero">
    <div style="font-size:0.82rem; letter-spacing:2px;
                color:#8EDCE0; font-weight:700;">
        CYBERSECURITY RESEARCH • REMOTE PATIENT MONITORING
    </div>
    <h1>Adaptive QKD–PQC Security Framework</h1>
    <p>
        An adaptive security framework using simulated quantum key
        distribution, hybrid anomaly detection and cryptographic
        integrity evaluation.
    </p>
</div>
""", unsafe_allow_html=True)

st.markdown(
    f'<a href="{GITHUB_URL}" target="_blank">'
    '↗ Explore source code and experiment documentation on GitHub'
    '</a>',
    unsafe_allow_html=True
)

st.markdown("""
<div class="notice">
    <b>Research prototype:</b> QKD is software-simulated. PQC fallback
    represents an abstract software-mode transition. AES-GCM uses
    independently generated random placeholder keys, not actual
    QKD-derived or ML-KEM-derived keys. This is not a production
    security system.
</div>
""", unsafe_allow_html=True)


# --------------------------------------------------
# OVERVIEW
# --------------------------------------------------

section_heading(
    "PROJECT OVERVIEW",
    "Simulation at a glance",
    "Summary of the available experiment outputs."
)

if qkd is not None and not qkd.empty:
    total_observations = len(qkd)
    average_rate = qkd["qkd_key_rate_bps"].mean()
    average_qber = qkd["qber"].mean()
    degraded_count = int(
        (qkd["channel_status"] == "DEGRADED").sum()
    )

    cols = st.columns(4)
    with cols[0]:
        metric_card("Observations", f"{total_observations:,}",
                    "QKD simulation records")
    with cols[1]:
        metric_card("Average key rate", f"{average_rate:,.2f}",
                    "Bits per second")
    with cols[2]:
        metric_card("Average QBER", f"{average_qber:.4f}",
                    "Across all observations")
    with cols[3]:
        metric_card("Degraded observations", f"{degraded_count:,}",
                    "Channel degradation interval")
else:
    show_missing("QKD simulation result file was not found.")

st.divider()

# --------------------------------------------------
# ANALYSIS TABS
# --------------------------------------------------

tab1, tab2, tab3, tab4 = st.tabs([
    "QKD Simulation",
    "Anomaly Detection",
    "Controller Comparison",
    "AES-GCM Evaluation"
])


# --------------------------------------------------
# TAB 1: QKD SIMULATION
# --------------------------------------------------

with tab1:
    section_heading(
        "QUANTUM KEY DISTRIBUTION",
        "QKD channel performance",
        "Key generation rate and quantum bit error rate over time."
    )

    if qkd is not None and not qkd.empty:
        status_options = ["All"] + sorted(
            qkd["channel_status"].dropna().unique().tolist()
        )

        selected_status = st.selectbox(
            "Channel status filter",
            status_options,
            key="qkd_status"
        )

        filtered = qkd.copy()

        if selected_status != "All":
            filtered = filtered[
                filtered["channel_status"] == selected_status
            ]

        # Key generation rate chart
        fig, ax = plt.subplots(figsize=(12, 4.2))

        normal = filtered[
            filtered["channel_status"] == "NORMAL"
        ]
        degraded = filtered[
            filtered["channel_status"] == "DEGRADED"
        ]

        ax.plot(
            normal["time_seconds"],
            normal["qkd_key_rate_bps"],
            color="#1769AA",
            linewidth=1.5,
            label="Normal channel"
        )

        ax.scatter(
            degraded["time_seconds"],
            degraded["qkd_key_rate_bps"],
            color="#E67E22",
            s=13,
            label="Degraded channel",
            zorder=3
        )

        chart_style(ax, "Key rate (bits/second)")
        ax.legend(frameon=False)
        fig.tight_layout()
        st.pyplot(fig)
        plt.close(fig)

        # QBER chart
        st.markdown("#### Quantum bit error rate")

        fig, ax = plt.subplots(figsize=(12, 4.2))

        ax.plot(
            filtered["time_seconds"],
            filtered["qber"],
            color="#1769AA",
            linewidth=1.5,
            label="QBER"
        )

        degraded_qber = filtered[
            filtered["channel_status"] == "DEGRADED"
        ]

        ax.scatter(
            degraded_qber["time_seconds"],
            degraded_qber["qber"],
            color="#D94841",
            s=15,
            label="Degraded interval",
            zorder=3
        )

        # Explicit range prevents degraded QBER clipping
        ax.set_ylim(
            0,
            max(0.16, float(filtered["qber"].max()) * 1.12)
        )

        chart_style(ax, "QBER")
        ax.legend(frameon=False)
        fig.tight_layout()
        st.pyplot(fig)
        plt.close(fig)

        st.markdown("#### Simulation records")
        st.dataframe(filtered, use_container_width=True, height=300)

        st.download_button(
            "Download QKD data",
            filtered.to_csv(index=False),
            file_name="qkd_simulation_data.csv",
            mime="text/csv"
        )

    else:
        show_missing("QKD result file not found.")


# --------------------------------------------------
# TAB 2: ANOMALY DETECTION
# --------------------------------------------------

with tab2:
    section_heading(
        "HYBRID ANOMALY DETECTION",
        "Isolation Forest performance",
        "Evaluation of simulated channel degradation detection."
    )

    if anomaly is not None and not anomaly.empty:
        row = anomaly.iloc[0]

        cols = st.columns(4)

        with cols[0]:
            metric_card("Accuracy", f"{row['accuracy']*100:.2f}%")
        with cols[1]:
            metric_card("Precision", f"{row['precision']*100:.2f}%")
        with cols[2]:
            metric_card("Recall", f"{row['recall']*100:.2f}%")
        with cols[3]:
            metric_card("F1-score", f"{row['f1_score']*100:.2f}%")

        st.markdown("#### Confusion matrix")

        matrix = pd.DataFrame(
            [
                [int(row["true_negatives"]),
                 int(row["false_positives"])],
                [int(row["false_negatives"]),
                 int(row["true_positives"])]
            ],
            index=["Predicted normal", "Predicted anomaly"],
            columns=["Actual normal", "Actual degraded"]
        )

        fig, ax = plt.subplots(figsize=(7, 3.8))
        image = ax.imshow(matrix.values, cmap="Blues")

        ax.set_xticks([0, 1], labels=matrix.columns)
        ax.set_yticks([0, 1], labels=matrix.index)

        for i in range(2):
            for j in range(2):
                ax.text(
                    j, i, str(matrix.iloc[i, j]),
                    ha="center", va="center",
                    fontsize=15, fontweight="bold",
                    color="#15324B"
                )

        ax.set_title("Classification results")
        fig.colorbar(image, ax=ax, fraction=0.035)
        fig.tight_layout()
        st.pyplot(fig)
        plt.close(fig)

        st.caption(
            f"Training samples: {int(row['training_samples'])} | "
            f"Total samples: {int(row['total_samples'])} | "
            f"Detected anomalies: {int(row['detected_anomalies'])}"
        )

        st.markdown("""
        <div class="notice">
            <b>Interpretation:</b> The detector evaluates simulated
            communication-channel degradation. It does not identify
            patient health anomalies or establish validated cyberattack
            detection capability.
        </div>
        """, unsafe_allow_html=True)

    else:
        show_missing("Anomaly detection metrics were not found.")


# --------------------------------------------------
# TAB 3: CONTROLLER COMPARISON
# --------------------------------------------------

with tab3:
    section_heading(
        "ADAPTIVE CONTROLLER ANALYSIS",
        "V5 baseline vs V5 + Isolation Forest",
        "Comparison of the available controller experiment outputs."
    )

    if comparison is not None and not comparison.empty:
        st.dataframe(comparison, use_container_width=True)

        numeric = comparison.copy()
        numeric["V5_baseline"] = pd.to_numeric(
            numeric["V5_baseline"], errors="coerce"
        )
        numeric["V5_plus_IF"] = pd.to_numeric(
            numeric["V5_plus_IF"], errors="coerce"
        )

        chart_data = numeric.dropna(
            subset=["V5_baseline", "V5_plus_IF"]
        )

        if not chart_data.empty:
            st.markdown("#### Metric comparison")

            fig, ax = plt.subplots(figsize=(11, 4.5))

            x = range(len(chart_data))
            width = 0.36

            ax.bar(
                [i - width/2 for i in x],
                chart_data["V5_baseline"],
                width,
                label="V5 baseline",
                color="#1769AA"
            )

            ax.bar(
                [i + width/2 for i in x],
                chart_data["V5_plus_IF"],
                width,
                label="V5 + IF",
                color="#159A91"
            )

            ax.set_xticks(
                list(x),
                labels=chart_data["metric"],
                rotation=35,
                ha="right"
            )

            chart_style(ax, "Recorded value", "Metric")
            ax.legend(frameon=False)
            fig.tight_layout()
            st.pyplot(fig)
            plt.close(fig)

        st.download_button(
            "Download controller comparison",
            comparison.to_csv(index=False),
            file_name="controller_comparison.csv",
            mime="text/csv"
        )

        st.markdown("""
        <div class="notice">
            A single experiment does not establish overall superiority
            of either controller. Multi-seed robustness results should
            be considered separately.
        </div>
        """, unsafe_allow_html=True)

    else:
        show_missing("Controller comparison file not found.")


# --------------------------------------------------
# TAB 4: AES-GCM
# --------------------------------------------------

with tab4:
    section_heading(
        "CRYPTOGRAPHIC INTEGRITY EVALUATION",
        "AES-256-GCM round-trip verification",
        "Packet encryption, decryption and integrity-test summary."
    )

    if aes is not None:
        cols = st.columns(4)

        with cols[0]:
            metric_card("Input packets", f"{aes['total_packets']:,}")
        with cols[1]:
            metric_card("Encrypted", f"{aes['encrypted_packets']:,}")
        with cols[2]:
            metric_card("Verified", f"{aes['verified_packets']:,}")
        with cols[3]:
            metric_card("Round-trip failures",
                        f"{aes['round_trip_failures']:,}")

        st.markdown("#### Integrity verification")

        checks = aes.get("additional_integrity_tests", {})

        for name, passed in checks.items():
            symbol = "✅" if passed else "❌"
            label = name.replace("_", " ").title()
            st.markdown(f"{symbol} **{label}**")

        if aes.get("all_integrity_tests_passed", False):
            st.success("All recorded integrity tests passed.")
        else:
            st.error("One or more integrity tests did not pass.")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### Cryptographic configuration")
            st.write("Algorithm:", aes.get("aes_algorithm"))
            st.write("Key size:", aes.get("aes_key_size_bits"), "bits")
            st.write("Nonce size:", aes.get("nonce_size_bytes"), "bytes")
            st.write(
                "Authentication tag:",
                aes.get("authentication_tag_size_bytes"),
                "bytes"
            )

        with col2:
            st.markdown("#### Processing summary")
            st.write("Sessions:", aes.get("number_of_sessions"))
            st.write("Key epochs:", aes.get("number_of_key_epochs"))
            st.write("Unique nonces:", aes.get("unique_nonces"))
            st.write(
                "Encryption time:",
                f"{aes.get('encryption_time_seconds', 0):.4f} seconds"
            )

        st.markdown("""
        <div class="notice">
            <b>Key-source limitation:</b> AES-GCM uses independently
            generated random simulation placeholder keys. These are
            not actual QKD-derived keys or ML-KEM-derived keys.
        </div>
        """, unsafe_allow_html=True)

    else:
        show_missing("AES-GCM summary JSON was not found.")


# --------------------------------------------------
# FOOTER
# --------------------------------------------------

st.markdown("""
<div class="footer">
    <b>Adaptive QKD–PQC Security Framework</b><br>
    Academic software simulation | Remote Patient Monitoring<br>
    Results are based on the locally available experiment output files.
    Interpret all metrics within the documented simulation scope.
</div>
""", unsafe_allow_html=True)
