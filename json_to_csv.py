import json
import csv

# Load JSON from file
with open('historical_rates.json', 'r') as f:
    data = json.load(f)

base_currency = data['source']
timestamp = data['date']  # Use 'date' for human-readable, or str(data['timestamp']) for epoch

# Prepare CSV output
with open('historical_rates.csv', 'w', newline='') as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(['BASE_CURRENCY', 'QUOTE_CURRENCY', 'EXCHANGE_RATE', 'TIMESTAMP'])
    for pair, rate in data['quotes'].items():
        # Remove 'USD' prefix to get quote currency
        quote_currency = pair.replace(base_currency, '')
        writer.writerow([base_currency, quote_currency, rate, timestamp])

print("CSV file 'historical_rates.csv' created successfully.")