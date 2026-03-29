import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
import matplotlib.pyplot as plt

# ---------------------------
# 1. Load data
# ---------------------------
df = pd.read_csv("data/all/sleep_diary.csv")

# ---------------------------
# 2. Helper: convert HH:MM → float hours
# ---------------------------
def time_to_hours(t):
    if pd.isna(t):
        return np.nan
    h, m, _ = map(int, t.split(":"))
    return h + m / 60

for col in ["go2bed", "asleep", "wakeup"]:
    df[col] = df[col].apply(time_to_hours)

# Account for the fact that wakeup times after midnight are technically smaller than go2bed times
df["go2bed"] = df.apply(lambda row: row["go2bed"] + 24 if row["go2bed"] < row["wakeup"] else row["go2bed"], axis=1)

# ---------------------------
# 3. Cyclical encoding (IMPORTANT)
# ---------------------------
def cyclical_encode(series, max_val=24):
    return np.sin(2 * np.pi * series / max_val), np.cos(2 * np.pi * series / max_val)

for col in ["go2bed", "asleep", "wakeup"]:
    df[f"{col}_sin"], df[f"{col}_cos"] = cyclical_encode(df[col])

df_user = df.groupby("userId").agg({
    "go2bed_sin": "mean",
    "go2bed_cos": "mean",
    "asleep_sin": "mean",
    "asleep_cos": "mean",
    "wakeup_sin": "mean",
    "wakeup_cos": "mean",
    "wakeup@night": "mean",
    "waso": "mean",
    "sleep_duration": "mean",
    "in_bed_duration": "mean",
    "sleep_latency": "mean",
    "sleep_efficiency": "mean"
}).reset_index()

# Save to CSV for later use
df_user.to_csv("sleep_features_by_user.csv", index=False)

# ---------------------------
# 4. Feature selection
# ---------------------------
features = [
    # time (encoded)
    "go2bed_sin", "go2bed_cos",
    "asleep_sin", "asleep_cos",
    "wakeup_sin", "wakeup_cos",

    # behavior
    "wakeup@night",
    "waso",
    "sleep_duration",
    "in_bed_duration",
    "sleep_latency",
    "sleep_efficiency"
]

X = df_user[features].dropna()

# ---------------------------
# 5. Scaling
# ---------------------------
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# ---------------------------
# 6. Find optimal number of clusters
# ---------------------------
k_range = range(2, 11)
sil_scores = []

for k in k_range:
    kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
    labels = kmeans.fit_predict(X_scaled)
    score = silhouette_score(X_scaled, labels)
    sil_scores.append(score)

# Plot silhouette scores
plt.plot(k_range, sil_scores, marker='o')
plt.xlabel("Number of clusters (k)")
plt.ylabel("Silhouette Score")
plt.title("Choosing k")
plt.show()

# Best k
best_k = k_range[np.argmax(sil_scores)]
print(f"Best k: {best_k}")

# ---------------------------
# 7. Final clustering
# ---------------------------
kmeans = KMeans(n_clusters=best_k, random_state=42, n_init=10)
df_user.loc[X.index, "cluster"] = kmeans.fit_predict(X_scaled)

# ---------------------------
# 8. Inspect clusters
# ---------------------------
def cyclical_to_hour(sin_val, cos_val, max_val=24):
    angle = np.arctan2(sin_val, cos_val)
    if angle < 0:
        angle += 2 * np.pi
    return angle * max_val / (2 * np.pi)

cluster_summary = df_user.groupby("cluster")[[
    "go2bed_sin", "go2bed_cos",
    "asleep_sin", "asleep_cos",
    "wakeup_sin", "wakeup_cos",
    "wakeup@night",
    "waso",
    "sleep_duration",
    "in_bed_duration",
    "sleep_latency",
    "sleep_efficiency"
]].mean()

cluster_summary["go2bed_hour"] = cluster_summary.apply(
    lambda row: cyclical_to_hour(row["go2bed_sin"], row["go2bed_cos"]), axis=1
)
cluster_summary["asleep_hour"] = cluster_summary.apply(
    lambda row: cyclical_to_hour(row["asleep_sin"], row["asleep_cos"]), axis=1
)
cluster_summary["wakeup_hour"] = cluster_summary.apply(
    lambda row: cyclical_to_hour(row["wakeup_sin"], row["wakeup_cos"]), axis=1
)

print(cluster_summary[[
    "go2bed_hour",
    "asleep_hour",
    "wakeup_hour",
    "wakeup@night",
    "waso",
    "sleep_duration",
    "in_bed_duration",
    "sleep_latency",
    "sleep_efficiency"
]].round(2))

# ---------------------------
# 9. Cluster sizes
# ---------------------------
print("\nCluster sizes:")
print(df_user["cluster"].value_counts())