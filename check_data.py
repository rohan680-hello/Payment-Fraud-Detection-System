import pandas as pd

df = pd.read_csv("data/creditcard.csv")

print("Dataset shape:", df.shape)
print("\nFirst five rows:")
print(df.head())
print("\nClass counts:")
print(df["Class"].value_counts())
print("\nMissing values:", df.isna().sum().sum())