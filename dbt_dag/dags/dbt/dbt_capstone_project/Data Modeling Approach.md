# Data Modeling Approach: Dimensional Modeling (Star Schema)

For this project, I used the **Dimensional Modeling** approach, also called a **Star Schema**, because it’s simple and great for analytics.

## Why use this approach?
- **Easy to understand:** Data is organized into facts (numbers to analyze) and dimensions (descriptions, like currency codes).
- **Fast for reporting:** Makes it quick to get answers from the data.
- **Flexible:** Easy to add new information later.

## How it works in this project

### Fact Table
- **exchange_metrics**: Stores the main numbers, like exchange rates, previous rates, and percentage changes.

### Dimensions
- **base_currency** and **quote_currency**: The currency codes.
- **timestamp**: The time of the exchange rate.

### Data Flow
- Raw data goes into **exchange_rates** (Bronze layer).
- Cleaned and deduplicated data is in **clean_exchange_rates** (Silver layer).
- Calculated metrics are in **exchange_metrics** (Gold layer).

## Relationships

- **clean_exchange_rates** is derived from **exchange_rates**  
  (maps `base_currency`, `quote_currency`, `timestamp` to `base_currency`, `quote_currency`, `timestamp_utc`).
- **exchange_metrics** is derived from **clean_exchange_rates**  
  (maps `base_currency`, `quote_currency`, `timestamp_utc` to `base_currency`, `quote_currency`, `timestamp`).

## Benefits

- Makes it easy to analyze exchange rates over time.
- Simple to create reports on currency trends.
- Keeps raw, cleaned, and final data separate for clarity.

---

**In summary:**  
Dimensional modeling was chosen because it’s clear, fast, and perfect for analyzing exchange rate data.