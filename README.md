# Zomato Pipeline

A Snowflake-based Zomato analytics pipeline. Local CSV data is loaded into Snowflake RAW tables, dbt transforms it into staging and marts, and Gemini-powered tools analyze reviews or generate SQL.

## Flow

```text
 data/*.csv
     |
 Airflow COPY tasks -> ZOMATO.RAW
     |
 dbt staging models -> ZOMATO.STAGING
     |
 dbt marts          -> ZOMATO.MARTS
     |
 review enrichment  -> ZOMATO.AI.REVIEW_ENRICHED
     |
 dbt AI model       -> review sentiment/topic aggregates
```

The scheduled Airflow DAG is `airflow/dags/zomato_batch.py`:

1. Copy restaurant, user, food, menu, order, order-item, and review files from the Snowflake stage.
2. Run dbt while excluding the `ai` tag.
3. Enrich up to five new reviews with Gemini.
4. Build the dbt models tagged `ai`.

## Repository layout

- `data/`: source CSV files.
- `zomato/`: dbt project, including staging models, dimensions, incremental facts, marts, tests, and macros.
- `airflow/`: Docker Compose deployment, image definition, and the batch DAG.
- `ai/enrich_reviews.py`: classifies reviews and writes `AI.REVIEW_ENRICHED`.
- `ai/text_to_sql.py`: Streamlit app that turns natural-language questions into Snowflake SQL.
- `ai/rag_chat.py`: Streamlit review search and question-answering app using embeddings.
- `ai/grab_sql.py`: combines dbt SQL files into `zomato/all_sql_files.txt`.
- `tests/unit/`: Python unit tests.
- `logs/` and `zomato/target/`: generated runtime and dbt artifacts.

## Prerequisites

- Python with the dependencies used by `ai/` and `tests/` (`snowflake-connector-python`, `google-genai`, `python-dotenv`, `pandas`, `numpy`, `streamlit`, `pyarrow`, and `pytest`).
- A Snowflake account with the `ZOMATO` database, `RAW`, `STAGING`, `MARTS`, and `AI` schemas, a warehouse, and a stage named `ZOMATO_RAW_STAGE`.
- dbt Core with the Snowflake adapter. Airflow's image installs `dbt-snowflake==1.8.*` in `/opt/airflow/dbt_venv`.
- Docker Desktop for the Airflow workflow.
- Gemini API access for the AI scripts.

Set these variables before running AI scripts: `GEMINI_API_KEY`, `SNOWFLAKE_ACCOUNT`, `SNOWFLAKE_USER`, `SNOWFLAKE_PASSWORD`, `SNOWFLAKE_WAREHOUSE`, `SNOWFLAKE_DATABASE`, and `SNOWFLAKE_SCHEMA`. The AI scripts load `ai/.env`; Airflow loads `airflow/.env` through Docker Compose.

## Run dbt locally

```powershell
cd zomato
dbt debug --profiles-dir .
dbt build --profiles-dir .
```

Use `dbt test --profiles-dir .` to run model tests. The dbt profile targets Snowflake and uses `ZOMATO` as the database. Staging models are views; marts are tables, with order facts configured as incremental merge models.

## Run Airflow

From `airflow/`:

```powershell
docker compose build
docker compose up -d
```

Open `http://localhost:8080` and sign in with the local credentials configured by `airflow-init`. Trigger `zomato_batch` after the Snowflake stage and connection are configured.

```powershell
docker compose down
```

## Run AI tools

From the repository root, after configuring `ai/.env`:

```powershell
python ai/enrich_reviews.py
streamlit run ai/text_to_sql.py
streamlit run ai/rag_chat.py
```

`rag_chat.py` caches sampled review embeddings in `review_embeddings_cache.parquet`. `text_to_sql.py` queries the marts described in its system prompt.

## Tests and SQL snapshot

```powershell
pytest -q
python ai/grab_sql.py
```

`grab_sql.py` regenerates `zomato/all_sql_files.txt` from the dbt project's SQL files.

## Security

Do not commit credentials or API keys. The repository currently contains credential-bearing environment/profile files; rotate exposed secrets, remove them from version control, and use local untracked `.env` files or a secret manager instead.
