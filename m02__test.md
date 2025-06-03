![Foundry Data & AI Academy Logo](https://raw.githubusercontent.com/foundry-ai-academy/fa-cdn/1.0.0/images/FoundryAI_academy_logo_on_yellow_space.png)

# Module 02 Test

## Test Requirement

Build a data system that incorporates:

- Real-time or near-real-time data ingestion using Kafka (or similar)
- Batch processing using dbt
- A simple ML model deployed on Snowflake (or similar)

## Submission

📤 Submission Requirements:

- 🌟 Code Repository
  - Submit your GitHub/GitLab repository link to trainers before your presentation slot. Ensure all trainers have access.
  - Early submission is encouraged - especially during your 1:1 consultation session - trainers will review your code and documentation beforehand. However, only the final state will be evaluated, as trainers will review your repository right before your presentation to account for any last-minute changes.
  - `Repo documentation is NOT graded` but helps streamline your presentation
  - Recommended README.md content:
    - Project overview and architecture
    - Setup instructions and dependencies
    - Key features and implementation challenges
    - Project structure (src/, docs/, tests/, etc.)
  - Documentation should be concise 🎬`(reading time < 5 minutes)`🎬

> [!WARNING] 
> 🚨 Live Demo Requirements:
>   - Criteria marked with `#live-demo` require successful execution during presentation
>   - If live demo fails, show successful execution logs from within 1 hour of presentation
>   - Criteria without `#live-demo` tag will be evaluated based on implementation only
- Book your presentation slot for this Module ASAP. If you can't make it work with the designated slot on Week 05 of this Module, contact your trainers
- Presentation duration: 15 minutes per trainee

> [!IMPORTANT]
>
> You only have 15 minutes - make every second count!
>
> Follow the grading criteria as your presentation outline and go straight to the point. For each criterion, quickly show us that you've met it
>
> Example: "For pipeline setup, I got 1 API call. The data is then sent to Snowflake. Here's how it works. `** Execute code **`. Here are the new data on Snowflake that have just been ingested, proven by timestamp."
>
> No fancy slides, no lengthy explanations - just show us that it works.
>
> This structured approach ensures you cover all required points within the tight time limit.

## Grading Criteria


| Category                                      | Criteria                                                                                                                                                                                                                                                                                                                                                     | Points               |
| ----------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------- |
| **CI/CD Setup**                               | `#live-demo` A working GitHub Action (or similar CI/CD pipeline) that successfully runs at least 2 automated checks (e.g., dbt test, lint) on PR commits.                                                                                                                                                                                                                 | 5                    |
| **Streaming Data Ingestion**                  | A Kafka (or similar) pipeline is successfully implemented, with at least 01 topic and 01 consumer.                                                                                                                                                                                                                                                           | 10                   |
|                                               | `#live-demo` New events successfully landed in Snowflake (or similar) in real-time or near-real-time (accepted data latency is <= 5 minutes)                                                                                                                                                                                                                              | 5                    |
| **dbt Project Setup & Development**           | The dbt project is properly configured with Snowflake (or similar) and has at least one scheduled job running via dbt Cloud, Airflow, or similar orchestration tool.                                                                                                                                                                                         | 5                    |
|                                               | `#live-demo` At least 03 dbt models are created and materialized successfully in different layers (e.g., medallion architecture).                                                                                                                                                                                                                                         | 5                    |
|                                               | `#live-demo` At least one incremental materialization implemented and successfully processing new data (not a full-refresh run).                                                                                                                                                                                                                                                | 5                    |
|                                               | `#live-demo` At least 01 dbt generic test (.yml) and 01 dbt singular test (sql) implemented and executed successfully (the test itself doesn't need to pass).                                                                                                                                                                                                             | 5                    |
|                                               | `#live-demo` At least one custom dbt macro or Jinja block implemented and working.                                                                                                                                                                                                                                                                                        | 5                    |
|                                               | At least 3 columns of the final dbt model(s) are documented (e.g., creating schema.yml file)                                                                                                                                                                                                                                                                 | 5                    |
| **Data Modeling**                             | A data modeling approach documented with an ERD (in draw.io or similar).                                                                                                                                                                                                                                                                                     | 5                    |
|                                               | Clear explanation of the chosen modeling approach (Data Vault, Dimensional, 3NF, OneBigTable ...) in a project markdown document.                                                                                                                                                                                                                            | 5                    |
| **ML Model Deployment & Prediction Pipeline** | A basic ML model (e.g., regression, classification) `implemented` with `code proof` (python scripts, notebook ...) that includes the following steps: data processing, feature selection, model training, evaluation, and monitoring.                                                                                                                                                                                                                                                                                   | 5                   |
|                                               | `#live-demo` ML model successfully executed (result doesn't have to be correct).                                                                                                                                                                                                                                                                                            | 5                    |
|                                               | ML model inference is orchestrated using any available tool of choice (e.g., Snowflake, dbt, Airflow).                                                                                                                                                                                                                                                                                            | 5                    |
| **Bonus & Creativity (Impress Us!)**          | Uses at least one additional tool/platform not covered in this module (e.g., Prefect, Databricks, BigQuery, etc.). Bonus points are awarded once per tool/platform across the entire course (e.g. if you've already received extra points for using BigQuery in a previous module test, you won't receive additional points for using it again in this test) | 10                   |
|                                               | Implements innovative/advance features (e.g. Kafka DLQ, DataVault 2.0 transactional links, advanced dbt techniques, dynamic models, advanced macros, custom generic test, dbt artifacts usage ...). Anything, really :shrug: - impress us!                                                                                                                   | 5 per feature, 5 max |

🔹 Total: 100 points

✅ Pass if ≥ 50 points

> [!NOTE]
>
> The total points are capped at 100. Any extra points exceeding 100 will be ignored.

## EXTRA: Helping is always encouraged

If you have proven track records of helping other students with their project/tests, you get extra +10. You decide on where to use this bonus (before weighted): this test, next test, or capstone project.

### Note

- Recommended to combine this with your capstone project
- Make it as simple as possible, pay attention to grading criteria
- This is an individual test - results will be evaluated by individual submission (but helping others is always encouraged)
- Since this is a test, you only have "limited" support from trainers (will decide case by case)

---

© 2024 Foundry Data & AI Academy.

All rights reserved.

This material is confidential and proprietary to Foundry Data & AI Academy. It may not be reproduced, transmitted, or stored, in whole or in part, in any form or by any means without written permission from Foundry Data & AI Academy.

![Foundry Data & AI Academy Logo](https://raw.githubusercontent.com/foundry-ai-academy/fa-cdn/1.0.0/images/FoundryAI_academy_logo_symbol_yellow_space.png)
