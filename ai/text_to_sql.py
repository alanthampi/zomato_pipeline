import json
import os 
import pandas as pd
import numpy as np
import streamlit as st
from google import genai
import snowflake.connector
from dotenv import load_dotenv
load_dotenv()

MODEL = "gemini-3.6-flash"
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
SYSTEM_PROMPT = """
You are an expert Snowflake SQL data analyst for a Zomato analytics data warehouse.

Use the following available tables and columns to understand the database schema and generate SQL queries based on the user's natural-language question.

DATABASE: ZOMATO

MARTS TABLES:

1. ZOMATO.MARTS.DIM_CUSTOMERS
Columns:
- customer_id
- customer_name
- email
- age
- gender
- marital_status
- occupation
- income_band
- education

2. ZOMATO.MARTS.DIM_DATE
Columns:
- order_date
- order_year
- order_month
- order_month_name
- order_day_name
- is_weekend

3. ZOMATO.MARTS.DIM_FOOD
Columns:
- food_name
- veg_or_non_veg

4. ZOMATO.MARTS.DIM_MENU
Columns:
- menu_id
- restaurant_id
- food_id
- cuisine
- price

5. ZOMATO.MARTS.DIM_RESTAURANTS
Columns:
- restaurant_id
- restaurant_name
- city
- cuisine
- rating
- rating_count
- cost_for_two
- license_no

6. ZOMATO.MARTS.FCT_ORDERS
Columns:
- order_id
- order_timestamp
- order_date
- customer_id
- restaurant_id
- city
- cuisine
- payment_method
- order_status
- is_delivered
- items_count
- sales_qty
- subtotal
- discount
- delivery_fee
- gst
- sales_amount
- customer_rating
- delivery_time_min

7. ZOMATO.MARTS.FCT_ORDER_ITEMS
Columns:
- order_item_id
- order_id
- restaurant_id
- f_id
- order_ts
- order_date
- city
- price
- quantity
- line_amount

8. ZOMATO.MARTS.MART_DAILY_CITY_REVENUE
Columns:
- city
- order_date
- total_orders
- total_revenue
- total_delivered
- cancellation_rate
- avg_order_value

9. ZOMATO.MARTS.MART_RESTAURANT_PERFORMANCE
Columns:
- restaurant_id
- cuisine
- avg_restaurant_rating
- total_res_reviews
- order_date
- total_sales
- city
- avg_order_rating
- avg_delivery_time
- orders


STAGING TABLES:

1. ZOMATO.STAGING.STG_USERS
Columns:
- customer_id
- customer_name
- email
- age
- gender
- marital_status
- occupation
- income_band
- education
- family_size

2. ZOMATO.STAGING.STG_RESTAURANTS
Columns:
- restaurant_id
- restaurant_name
- city
- rating
- rating_count
- cost_for_two
- cuisine
- license_no

3. ZOMATO.STAGING.STG_ORDERS
Columns:
- order_id
- order_timestamp
- order_date
- customer_id
- restaurant_id
- city
- cuisine
- items_count
- sales_qty
- subtotal
- discount
- delivery_fee
- gst
- sales_amount
- currency
- payment_method
- order_status
- is_delivered
- customer_rating
- delivery_time_min

4. ZOMATO.STAGING.STG_ORDER_ITEMS
Columns:
- order_item_id
- order_id
- restaurant_id
- f_id
- price
- quantity
- line_amount

5. ZOMATO.STAGING.STG_REVIEWS
Columns:
- review_id
- order_id
- customer_id
- restaurant_id
- rating
- comment
- review_date
- city

6. ZOMATO.STAGING.STG_MENU
Columns:
- menu_id
- restaurant_id
- food_id
- cuisine
- price

7. ZOMATO.STAGING.STG_FOOD
Columns:
- f_id
- food_name
- veg_or_non_veg


RELATIONSHIPS:

- FCT_ORDERS.customer_id = DIM_CUSTOMERS.customer_id
- FCT_ORDERS.restaurant_id = DIM_RESTAURANTS.restaurant_id
- FCT_ORDERS.order_date = DIM_DATE.order_date
- FCT_ORDER_ITEMS.order_id = FCT_ORDERS.order_id
- FCT_ORDER_ITEMS.restaurant_id = DIM_RESTAURANTS.restaurant_id
- DIM_MENU.restaurant_id = DIM_RESTAURANTS.restaurant_id
- STG_REVIEWS.restaurant_id = STG_RESTAURANTS.restaurant_id
- STG_REVIEWS.customer_id = STG_USERS.customer_id
- STG_REVIEWS.order_id = STG_ORDERS.order_id

Use the MARTS tables whenever possible. Use STAGING tables only when the required data is not available in the MARTS tables.

Generate valid Snowflake SQL using only the tables and columns listed above.
constraint: 
1. all the non- sql words or comment must be commented 
"""

def ask_llm(question):
    response = client.models.generate_content(
        model=MODEL,
        contents=question,
        config=genai.types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0
        )
    )

    sql_query = response.text.strip()

    # Remove Markdown code fences
    sql_query = sql_query.replace("```sql", "")
    sql_query = sql_query.replace("```", "")

    # Remove SQL comment lines
    sql_query = "\n".join(
        line
        for line in sql_query.splitlines()
        if not line.strip().startswith("--")
    )

    return sql_query.strip()

def get_connection():
    return snowflake.connector.connect(
            user=os.getenv("SNOWFLAKE_USER"),
            password=os.getenv("SNOWFLAKE_PASSWORD"),
            account=os.getenv("SNOWFLAKE_ACCOUNT"),
            warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
            database=os.getenv("SNOWFLAKE_DATABASE"),
            schema=os.getenv("SNOWFLAKE_SCHEMA")
        )

def query_snowflake(sql_query):
    connection = get_connection()

    try:
        cursor = connection.cursor()
        cursor.execute(sql_query)

        results = cursor.fetchall()
        columns = [column[0] for column in cursor.description]

        return pd.DataFrame(results, columns=columns)

    finally:
        cursor.close()
        connection.close()

def main():
    st.title("Text to SQL")

    st.caption(
        f"Enter your query and the model will generate the SQL query "
        f"for you using the {MODEL} model."
    )

    st.sidebar.markdown("""
    ### Sample Questions

    1. Which cities generated the highest total revenue?
    2. What are the top 10 restaurants by total sales?
    3. What is the average delivery time for each city?
    4. What percentage of orders were cancelled in each month?
    5. Which payment method is used most frequently by customers?
    """)

    question = st.text_input(
        "Enter your question",
        placeholder="Enter your query here"
    )

    if st.button("Generate SQL"):
        if question.strip():
            sql_query = ask_llm(question)

            st.subheader("Generated SQL")
            st.code(sql_query, language="sql")

            answer = query_snowflake(sql_query)

            st.subheader("Query Result")
            st.dataframe(answer, use_container_width=True)
        else:
            st.warning("Please enter a question first.")


if __name__ == "__main__":
    main()