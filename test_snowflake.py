from dotenv import load_dotenv
import snowflake.connector
import os
load_dotenv('secret.env')
# Connect to Snowflake
conn = snowflake.connector.connect(
    user=os.getenv("SNOWFLAKE_USER"),
    password=os.getenv("SNOWFLAKE_PASSWORD"),
    account=os.getenv("SNOWFLAKE_ACCOUNT"),
    warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
    database=os.getenv("SNOWFLAKE_DATABASE"),
    schema=os.getenv("SNOWFLAKE_SCHEMA")
)
cursor = conn.cursor()

cursor.execute("SELECT CURRENT_VERSION()")
version = cursor.fetchone()
print(version)
# Close the cursor and connection
cursor.close()
conn.close()