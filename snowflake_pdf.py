from dotenv import load_dotenv
import os
from snowflake import connector
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

# Load environment variables from .env file
load_dotenv()

# Connect to Snowflake using environment variables
conn = connector.connect(
    user=os.getenv('SNOWFLAKE_USER'),
    password=os.getenv('SNOWFLAKE_PASSWORD'),
    account=os.getenv('SNOWFLAKE_ACCOUNT'),
    warehouse=os.getenv('SNOWFLAKE_WAREHOUSE'),
    database=os.getenv('SNOWFLAKE_DATABASE'),
    schema=os.getenv('SNOWFLAKE_SCHEMA')
)

# ...existing code...

# Query FX analysis
cur = conn.cursor()
cur.execute("SELECT section, content FROM fx_analysis ORDER BY section;")
rows = cur.fetchall()

# Set up PDF document
doc = SimpleDocTemplate("forex_analysis.pdf")
styles = getSampleStyleSheet()
elements = []

for section, content in rows:
    elements.append(Paragraph(f"<b>{section}</b>", styles['Heading2']))
    elements.append(Paragraph(content, styles['BodyText']))
    elements.append(Spacer(1, 12))

doc.build(elements)

print("✅ PDF generated: forex_analysis.pdf")
