import pandas as pd
import matplotlib.pyplot as plt 

# Import the cluster summary data
clustered_users = pd.read_csv("clustered_users.csv")
# Import survey response data
survey_data = pd.read_csv("data/all/survey.csv")
# Merge the clustered user data with the survey responses
clustered_users = pd.merge(clustered_users, survey_data, left_on="userId", right_on="deviceId")

# See the per-cluster most common values for...
## regular column
print("Life regularity by cluster:")
print(clustered_users.groupby("cluster")["regular"].agg(lambda x: x.mean()))
## exercise column
print("\nExercise frequency by cluster:")
print(clustered_users.groupby("cluster")["exercise"].agg(lambda x: x.mean()))
## coffee drinking column
print("\nCoffee drinking by cluster:")
print(clustered_users.groupby("cluster")["coffee"].agg(lambda x: x.mean()))
## smoking column
print("\nSmoking by cluster:")
print(clustered_users.groupby("cluster")["smoking"].agg(lambda x: x.mean()))
## alcohol column
print("\nAlcohol consumption by cluster:")
print(clustered_users.groupby("cluster")["drinking"].agg(lambda x: x.mean()))

# For each of the following tests, find, for each user, the difference in score between start, middle and end of the study
test_names = ["ISI", "PHQ9", "GAD7"]
for test in test_names:
    print(f"\n===================\n{test} score changes by cluster:")
    clustered_users[f"{test}_start_value"] = clustered_users[f"{test}_1"]
    clustered_users[f"{test}_change_start_middle"] = clustered_users[f"{test}_2"] - clustered_users[f"{test}_1"]
    clustered_users[f"{test}_middle_value"] = clustered_users[f"{test}_2"]  
    clustered_users[f"{test}_change_middle_end"] = clustered_users[f"{test}_F"] - clustered_users[f"{test}_2"]
    clustered_users[f"{test}_end_value"] = clustered_users[f"{test}_F"]
    clustered_users[f"{test}_change_start_end"] = clustered_users[f"{test}_F"] - clustered_users[f"{test}_1"]
    print(clustered_users.groupby("cluster")[[f"{test}_start_value", f"{test}_change_start_middle", f"{test}_middle_value", f"{test}_change_middle_end", f"{test}_end_value", f"{test}_change_start_end"]].mean())

# Plot the change in scores over time for each cluster
for test in test_names:
    plt.figure(figsize=(10, 6))
    for cluster in clustered_users["cluster"].unique():
        cluster_data = clustered_users[clustered_users["cluster"] == cluster]
        plt.plot(["start", "middle", "end"], [cluster_data[f"{test}_start_value"].mean(), cluster_data[f"{test}_middle_value"].mean(), cluster_data[f"{test}_end_value"].mean()], marker='o', label=f"Cluster {cluster}")
    plt.title(f"{test} score changes over time by cluster")
    plt.xlabel("Time point")
    plt.ylabel(f"{test} score")
    plt.legend()
    plt.show()

# Do the same but plot everything in the same figure with 3 subplots
fig, ax = plt.subplots(1, 3, figsize=(15, 5))
for i, test in enumerate(test_names):
    for cluster in clustered_users["cluster"].unique():
        cluster_data = clustered_users[clustered_users["cluster"] == cluster]
        ax[i].plot(["start", "middle", "end"], [cluster_data[f"{test}_start_value"].mean(), cluster_data[f"{test}_middle_value"].mean(), cluster_data[f"{test}_end_value"].mean()], marker='o', label=f"Cluster {cluster}")
    ax[i].set_title(f"{test} score changes over time by cluster")
    ax[i].set_xlabel("Time point")
    ax[i].set_ylabel(f"{test} score")
    ax[i].legend()
plt.tight_layout()
plt.show()