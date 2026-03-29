import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
import matplotlib.pyplot as plt

# ---------------------------
# 1. Load data
# ---------------------------
df_sleep = pd.read_csv("sleep_features_by_user.csv")
df_wearable = pd.read_csv("wearable_features_by_user.csv")   

# Merge on userId/deviceId (assuming they are the same)
df_merged = pd.merge(df_sleep, df_wearable, left_on="userId", right_on="deviceId")

# Set data
X = df_merged.drop(columns=["userId", "deviceId"]).dropna()  # Drop any rows with NaN values

# Standardize features
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# Find optimal number of clusters using silhouette score
silhouette_scores = []
K_range = range(2, 10)
for K in K_range:
    kmeans = KMeans(n_clusters=K, random_state=42, n_init=10)
    labels = kmeans.fit_predict(X_scaled)
    score = silhouette_score(X_scaled, labels)
    silhouette_scores.append(score)

# Plot silhouette scores
plt.plot(K_range, silhouette_scores, marker='o')
plt.xlabel("Number of clusters (k)")
plt.ylabel("Silhouette Score")
plt.title("Choosing k")
plt.show()

# Best k
best_k = K_range[np.argmax(silhouette_scores)]
print(f"Best k: {best_k}")

# Fit final KMeans model
final_kmeans = KMeans(n_clusters=best_k, random_state=42, n_init=10)
df_merged["cluster"] = final_kmeans.fit_predict(X_scaled)
# Cluster sizes
print("\nCluster sizes:")
print(df_merged["cluster"].value_counts().sort_index())

# Inspect clusters
def cyclical_to_hour(sin_val, cos_val, max_val=24):
    angle = np.arctan2(sin_val, cos_val)
    if angle < 0:
        angle += 2 * np.pi
    return angle * max_val / (2 * np.pi)


cluster_summary = df_merged.groupby("cluster")[[
    "go2bed_sin", "go2bed_cos",
    "asleep_sin", "asleep_cos",
    "wakeup_sin", "wakeup_cos",
    "wakeup@night",
    "waso",
    "sleep_duration",
    "in_bed_duration",
    "sleep_latency",
    "sleep_efficiency",
    "HR_mean", "HR_std", "HR_p5", "HR_p95",
    "steps_total",
    "activity_total",
    "light_mean",
    "hrv_pca1", "hrv_pca2", "hrv_pca3", "hrv_pca4"
]].mean()
# Revert cyclical features back to hours for interpretability
cluster_summary["go2bed_hour"] = cluster_summary.apply(
    lambda row: cyclical_to_hour(row["go2bed_sin"], row["go2bed_cos"]), axis=1
)
cluster_summary["asleep_hour"] = cluster_summary.apply(
    lambda row: cyclical_to_hour(row["asleep_sin"], row["asleep_cos"]), axis=1
)
cluster_summary["wakeup_hour"] = cluster_summary.apply(
    lambda row: cyclical_to_hour(row["wakeup_sin"], row["wakeup_cos"]), axis=1
)
# Drop the cols
cluster_summary = cluster_summary.drop(columns=[
    "go2bed_sin", "go2bed_cos",
    "asleep_sin", "asleep_cos",
    "wakeup_sin", "wakeup_cos"
])

# Print cluster summary
print("\nCluster summary:")

cols_HR = ["HR_mean", "HR_std", "HR_p5", "HR_p95"]
cols_abstract = ["hrv_pca1", "hrv_pca2", "hrv_pca3", "hrv_pca4"]
cols_steps_activity_light = ["steps_total", "activity_total", "light_mean"]
cols_sleep = ["go2bed_hour", "asleep_hour", "wakeup_hour", "wakeup@night", "waso", "sleep_duration", "in_bed_duration", "sleep_latency", "sleep_efficiency"]
print(cluster_summary[cols_HR].round(2))
print(cluster_summary[cols_steps_activity_light].round(2))
print(cluster_summary[cols_sleep].round(2))
print(cluster_summary[cols_abstract].round(2))

# Save cluster summary to CSV
cluster_summary.to_csv("cluster_summary.csv")

# Save df_merged with cluster labels for later use
df_merged.to_csv("clustered_users.csv", index=False)