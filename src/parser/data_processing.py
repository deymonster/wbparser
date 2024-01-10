import pandas as pd

df = pd.read_csv('../sales_data_2023-07-07.csv', delimiter=',')
print(df.describe())