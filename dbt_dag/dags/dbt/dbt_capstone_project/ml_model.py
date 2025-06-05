import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error
import snowflake.connector
import numpy as np

# 1. Connect to Snowflake
conn = snowflake.connector.connect(
    user='USER_DBT_NGUYENLE',
    password='kaj123hsduwbHGG$',
    account='XATDYDZ-NF59370',
    warehouse='WH_DBT_NGUYENLE',
    database='CAPSTONE',
    schema='CAPSTONE.SC_LAB_M1W4_BRONZE'
)

# 2. Query data from your final dbt model (adjust table name as needed)
query = """
SELECT EXCHANGE_RATE, PCT_CHANGE
FROM SC_LAB_M1W4_Gold.exchange_metrics
WHERE PCT_CHANGE IS NOT NULL
LIMIT 100
"""
df = pd.read_sql(query, conn)

# 3. Feature selection (very simple: use exchange_rate to predict pct_change)
X = df[['EXCHANGE_RATE']]
y = df['PCT_CHANGE']

# 4. Model training
model = LinearRegression()
model.fit(X, y)

# 5. Evaluation
preds = model.predict(X)
rmse = np.sqrt(mean_squared_error(y, preds))
print(f"RMSE: {rmse:.4f}")

# 6. Monitoring: print model coefficients
print("Model coefficients:", model.coef_)
print("Model intercept:", model.intercept_)

# 7. Make a prediction (demo)
sample = pd.DataFrame({'EXCHANGE_RATE': [df['EXCHANGE_RATE'].mean()]})
prediction = model.predict(sample)
print(f"Predicted pct_change for mean exchange_rate: {prediction[0]:.4f}")

conn.close()