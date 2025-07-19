import os
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import snowflake.connector
from dotenv import load_dotenv

# Load environment variables for Snowflake credentials
load_dotenv()

# Connect to Snowflake using environment variables
conn = snowflake.connector.connect(
    user=os.getenv("SNOWFLAKE_USER"),
    password=os.getenv("SNOWFLAKE_PASSWORD"),
    account=os.getenv("SNOWFLAKE_ACCOUNT"),
    warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
    database=os.getenv("SNOWFLAKE_DATABASE"),
    schema=os.getenv("SNOWFLAKE_SCHEMA"),
    role=os.getenv("SNOWFLAKE_ROLE"),
)

# Query historical exchange rates from your mart table
query = """
SELECT QUOTE_CURRENCY, EXCHANGE_RATE, TIMESTAMP
FROM DB_SCHEMA.MART_EXCHANGE_RATES
ORDER BY QUOTE_CURRENCY, TIMESTAMP
"""
df = pd.read_sql(query, conn)
conn.close()

# Feature engineering: calculate rolling volatility (7-period rolling std of pct change)
df['rate_pct_change'] = df.groupby('QUOTE_CURRENCY')['EXCHANGE_RATE'].pct_change()
df['volatility'] = df.groupby('QUOTE_CURRENCY')['rate_pct_change'].rolling(window=7, min_periods=1).std().reset_index(0, drop=True)

# Labeling: assign high/medium/low volatility classes using quantiles
vol_q = df['volatility'].quantile([0.33, 0.66]).values
def label_vol(v):
    if v <= vol_q[0]:
        return 0  # low
    elif v <= vol_q[1]:
        return 1  # medium
    else:
        return 2  # high

df['vol_class'] = df['volatility'].apply(label_vol)
df = df.dropna(subset=['volatility', 'vol_class'])

# Prepare features and labels
X = df[['volatility']].values
y = df['vol_class'].values

# Train/test split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
clf = RandomForestClassifier(n_estimators=100, random_state=42)
clf.fit(X_train, y_train)

# Evaluate and print results
y_pred = clf.predict(X_test)
print("Classification Report:")
print(classification_report(
    y_test, y_pred,
    labels=[0, 1, 2],
    target_names=['Low', 'Medium', 'High']
))
# Predict volatility class for the most recent value
latest_row = df.dropna(subset=['volatility']).sort_values('TIMESTAMP').iloc[-1]
latest_vol = latest_row['volatility']
latest_currency = latest_row['QUOTE_CURRENCY']
latest_time = latest_row['TIMESTAMP']

pred_class = clf.predict(np.array([[latest_vol]]))[0]
class_names = ['Low', 'Medium', 'High']
print("Volatility quantile thresholds:", vol_q)
print(f"Latest volatility value: {latest_vol:.5f} for {latest_currency} at {latest_time}")
print(f"Predicted volatility class: {class_names[pred_class]}")

# Predict volatility class for the top 5 most recent values
top_n = 5
recent_rows = df.dropna(subset=['volatility']).sort_values('TIMESTAMP').tail(top_n)

predictions = []
for _, row in recent_rows.iterrows():
    vol = row['volatility']
    currency = row['QUOTE_CURRENCY']
    time = row['TIMESTAMP']
    time_str = str(time)
    pred_class = clf.predict(np.array([[vol]]))[0]
    predictions.append((time_str, currency, float(vol), class_names[pred_class]))

# Insert predictions into Snowflake
conn_insert = snowflake.connector.connect(
    user=os.getenv("SNOWFLAKE_USER"),
    password=os.getenv("SNOWFLAKE_PASSWORD"),
    account=os.getenv("SNOWFLAKE_ACCOUNT"),
    warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
    database=os.getenv("SNOWFLAKE_DATABASE"),
    schema=os.getenv("SNOWFLAKE_SCHEMA"),
    role=os.getenv("SNOWFLAKE_ROLE"),
)
insert_sql = """
INSERT INTO DB_SCHEMA.VOLATILITY_PREDICTIONS (TIMESTAMP, QUOTE_CURRENCY, VOLATILITY, PREDICTED_CLASS)
VALUES (%s, %s, %s, %s)
"""
with conn_insert.cursor() as cur:
    cur.executemany(insert_sql, predictions)
conn_insert.close()
print(f"\nInserted top {top_n} predictions into DB_SCHEMA.VOLATILITY_PREDICTIONS.")