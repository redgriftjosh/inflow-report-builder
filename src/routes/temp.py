import pandas as pd


data = {
    "Total_Flow": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]
}

df = pd.DataFrame(data)

df['15_Min_Avg_Flow'] = df['Total_Flow'][::-1].rolling(window=10, min_periods=1).mean()[::-1].fillna(0)

print(df.head(20))