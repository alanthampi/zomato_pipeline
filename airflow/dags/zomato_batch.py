from datetime import datetime
from airflow import DAG
from airflow.providers.common.sql.operators.sql import SQLExecuteQueryOperator
from airflow.providers.standard.operators.bash import BashOperator

DBT = "/opt/airflow/dbt_venv/bin/dbt"
DBT_PROJECT = "/opt/airflow/dbt/zomato"

COPY_RAW = [
"COPY INTO RAW.restaurants FROM @ZOMATO_RAW_STAGE/restaurant ON_ERROR = 'CONTINUE';",
"COPY INTO RAW.users FROM @ZOMATO_RAW_STAGE/users ON_ERROR = 'CONTINUE';",
"COPY INTO RAW.food FROM @ZOMATO_RAW_STAGE/food ON_ERROR = 'CONTINUE';",
"COPY INTO RAW.menu FROM @ZOMATO_RAW_STAGE/menu ON_ERROR = 'CONTINUE';",
"COPY INTO RAW.orders FROM @ZOMATO_RAW_STAGE/orders ON_ERROR = 'CONTINUE';",
"COPY INTO RAW.order_items FROM @ZOMATO_RAW_STAGE/order_items ON_ERROR = 'CONTINUE';",
"COPY INTO RAW.reviews FROM @ZOMATO_RAW_STAGE/reviews ON_ERROR = 'CONTINUE';"
]

with DAG(
    dag_id="zomato_batch",
    start_date=datetime(2024,1,1),
    schedule="@daily",
    catchup=False,
    tags=["zomato", "batch", "dbt"],
    doc_md=__doc__,

) as dag:
    reload_raw = SQLExecuteQueryOperator(
        task_id="reload_raw",
        conn_id="snowflake_default",
        sql=COPY_RAW,
        split_statements=True,
        autocommit=True
    )

    dbt_build_code = BashOperator(
        task_id="dbt_build_code",
        bash_command=f"{DBT} build --exclude tag:ai  --project-dir {DBT_PROJECT} --profiles-dir /opt/airflow/dbt/zomato")

    ai_enrichment_code = BashOperator(
        task_id = "ai_enrichment_code",
        bash_command=f"python /opt/airflow/ai/enrich_reviews.py"
    )

    dbt_build_ai_code = BashOperator(
        task_id = "dbt_build_ai_code",
        bash_command = f"{DBT} build --select tag:ai --project-dir {DBT_PROJECT} --profiles-dir {DBT_PROJECT} "
    )

    reload_raw >> dbt_build_code >> ai_enrichment_code >> dbt_build_ai_code