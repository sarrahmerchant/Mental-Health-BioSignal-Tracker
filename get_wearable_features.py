import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.decomposition import PCA

# ----------------------------
# 1. Load data
# ----------------------------
df = pd.read_csv("data/all/sensor_hrv_filtered.csv")

# For each unique patient ID, find:
# The minimal ts_start value
# Set the first ts_start value as the start of day 1 for that patient, then compute the start times of subsequent days as the minimal ts_start value + 1 day, + 2 days, etc.
# Create a new column in the dataframe that contains the day number for each ts_start value, computed as the number of days since the first ts_start value for that patient.
df["day"] = df.groupby("deviceId")["ts_start"].transform(lambda x: (x - x.min()) // (1000*3600*24) + 1)
# Sort the dataframe by deviceId and ts_start to ensure that the data is organized correctly for each patient
df = df.sort_values(by=["deviceId", "ts_start"]).reset_index(drop=True)

# Now the task is to aggregate data by patient and day
## 1. HR: compute mean, std, 5th percentile and 95th percentile (extreme variations) for each patient and day
hr_agg = df.groupby(["deviceId", "day"])["HR"].agg(["mean", "std", lambda x: np.percentile(x, 5), lambda x: np.percentile(x, 95)]).reset_index()
hr_agg.columns = ["deviceId", "day", "HR_mean", "HR_std", "HR_p5", "HR_p95"]
## 2. Steps: compute total steps for each patient and day
steps_agg = df.groupby(["deviceId", "day"])["steps"].sum().reset_index()
steps_agg.columns = ["deviceId", "day", "steps_total"]
## 3. Movement: use gyroscope data as a proxy for activity because steps is bad. 
### First compute the magnitude of the gyroscope data as sqrt(gyro_x^2 + gyro_y^2 + gyro_z^2)
df["gyro_magnitude"] = np.sqrt(df["gyr_x_avg"]**2 + df["gyr_y_avg"]**2 + df["gyr_z_avg"]**2)
### Then compute the total sum of mvmt for each patient and day
activity_agg = df.groupby(["deviceId", "day"])["gyro_magnitude"].sum().reset_index()
activity_agg.columns = ["deviceId", "day", "activity_total"]
## 4. Light exposure: compute mean light exposure for each patient and day
light_agg = df.groupby(["deviceId", "day"])["light_avg"].mean().reset_index()
light_agg.columns = ["deviceId", "day", "light_mean"]
## 5. HRV features
### 5.1 SDNN: standard deviation of NN intervals, mean and 5% and 95% percentiles for each patient and day
hrv_sdnn_agg = df.groupby(["deviceId", "day"])["sdnn"].agg(["mean", lambda x: np.percentile(x, 5), lambda x: np.percentile(x, 95)]).reset_index()
hrv_sdnn_agg.columns = ["deviceId", "day", "sdnn_mean", "sdnn_p5", "sdnn_p95"]
### 5.2 RMSSD: root mean square of successive differences between NN intervals, mean and 5% and 95% percentiles for each patient and day
hrv_rmssd_agg = df.groupby(["deviceId", "day"])["rmssd"].agg(["mean", lambda x: np.percentile(x, 5), lambda x: np.percentile(x, 95)]).reset_index()
hrv_rmssd_agg.columns = ["deviceId", "day", "rmssd_mean", "rmssd_p5", "rmssd_p95"]
### 5.3 SDSD: standard deviation of successive differences between NN intervals, mean and 5% and 95% percentiles for each patient and day
hrv_sdsd_agg = df.groupby(["deviceId", "day"])["sdsd"].agg(["mean", lambda x: np.percentile(x, 5), lambda x: np.percentile(x, 95)]).reset_index()
hrv_sdsd_agg.columns = ["deviceId", "day", "sdsd_mean", "sdsd_p5", "sdsd_p95"]
### 5.4 pNN20: percentage of successive NN intervals that differ by more than 20 ms
hrv_pnn20_agg = df.groupby(["deviceId", "day"])["pnn20"].mean().reset_index()
hrv_pnn20_agg.columns = ["deviceId", "day", "pnn20_mean"]
### 5.5 pNN50: percentage of successive NN intervals that differ by more than 50 ms
hrv_pnn50_agg = df.groupby(["deviceId", "day"])["pnn50"].mean().reset_index()
hrv_pnn50_agg.columns = ["deviceId", "day", "pnn50_mean"]
### 5.6 LF: low frequency power in the HRV spectrum, mean and 5% and 95% percentiles for each patient and day
hrv_lf_agg = df.groupby(["deviceId", "day"])["lf"].agg(["mean", lambda x: np.percentile(x, 5), lambda x: np.percentile(x, 95)]).reset_index()
hrv_lf_agg.columns = ["deviceId", "day", "lf_mean", "lf_p5", "lf_p95"]
### 5.7 HF: high frequency power in the HRV spectrum
hrv_hf_agg = df.groupby(["deviceId", "day"])["hf"].mean().reset_index()
hrv_hf_agg.columns = ["deviceId", "day", "hf_mean"]
### 5.8 LF/HF ratio: ratio of low frequency to high frequency power in the HRV spectrum, mean and 5% and 95% percentiles for each patient and day
hrv_lf_hf_agg = df.groupby(["deviceId", "day"])["lf/hf"].agg(["mean", lambda x: np.percentile(x, 5), lambda x: np.percentile(x, 95)]).reset_index()
hrv_lf_hf_agg.columns = ["deviceId", "day", "lf_hf_mean", "lf_hf_p5", "lf_hf_p95"]

# Now merge all the aggregated dataframes into a single dataframe for clustering
agg_df = hr_agg.merge(steps_agg, on=["deviceId", "day"]).merge(activity_agg, on=["deviceId", "day"]).merge(light_agg, on=["deviceId", "day"]).merge(hrv_sdnn_agg, on=["deviceId", "day"]).merge(hrv_rmssd_agg, on=["deviceId", "day"]).merge(hrv_sdsd_agg, on=["deviceId", "day"]).merge(hrv_pnn20_agg, on=["deviceId", "day"]).merge(hrv_pnn50_agg, on=["deviceId", "day"]).merge(hrv_lf_agg, on=["deviceId", "day"]).merge(hrv_hf_agg, on=["deviceId", "day"]).merge(hrv_lf_hf_agg, on=["deviceId", "day"])

# Now aggregate per patient by taking the mean of each feature across days for each patient, so we have one row per patient for clustering
patient_agg_df = agg_df.groupby("deviceId").mean().reset_index()
patient_agg_df.drop(columns=["day"], inplace=True)

# This is a lot of data. Let's do some dimentionality reduction on the HRV features using PCA to reduce the number of features for clustering. We will keep 2 principal components for visualization purposes.
hrv_features = ["sdnn_mean", "sdnn_p5", "sdnn_p95", "rmssd_mean", "rmssd_p5", "rmssd_p95", "sdsd_mean", "sdsd_p5", "sdsd_p95", "pnn20_mean", "pnn50_mean", "lf_mean", "lf_p5", "lf_p95", "hf_mean", "lf_hf_mean", "lf_hf_p5", "lf_hf_p95"]
scaler = StandardScaler()
hrv_scaled = scaler.fit_transform(patient_agg_df[hrv_features])
pca = PCA(n_components=4)
hrv_pca = pca.fit_transform(hrv_scaled)
patient_agg_df["hrv_pca1"] = hrv_pca[:, 0]
patient_agg_df["hrv_pca2"] = hrv_pca[:, 1]
patient_agg_df["hrv_pca3"] = hrv_pca[:, 2]
patient_agg_df["hrv_pca4"] = hrv_pca[:, 3]
patient_agg_df.drop(columns=hrv_features, inplace=True)

# Save to CSV for later use
patient_agg_df.to_csv("wearable_features_by_user.csv", index=False)

# Print some of info to interpret the 3 PCA components
# Look at how the original HRV features correlate with the 3 PCA components
hrv_feature_names = hrv_features
pca_df = pd.DataFrame(pca.components_, columns=hrv_feature_names, index=["PCA1", "PCA2", "PCA3", "PCA4"])
print("PCA components (correlation of original features with PCA components):")
print(pca_df[pca_df.columns[pca_df.columns.str.contains("sdnn|rmssd|sdsd")]])  # These are all time-domain HRV features, so they should load on the same component(s)
print(pca_df[pca_df.columns[pca_df.columns.str.contains("pnn20|pnn50")]])  # These are also time-domain HRV features, so they should load on the same component(s) as sdnn/rmssd/sdsd
print(pca_df[pca_df.columns[pca_df.columns.str.contains("lf|hf")]])  # These are frequency-domain HRV features, so they should load on the same component(s) but different from the time-domain features

for i in range(4):
    print(f"\nTop contributors to PCA{i+1}:")
    print(pca_df.iloc[i].sort_values(key=abs, ascending=False).head(8))
print(pca.explained_variance_ratio_)
print(pca.explained_variance_ratio_.cumsum())
