import json
import os 
import snowflake.connector
from google import genai
from dotenv import load_dotenv
from google.genai import types

load_dotenv()
MODEL = "gemini-3.6-flash"
SAMPLING = 5

TOPICS = [
    "food quality", "delivery time", "customer service", "app usability", "pricing", "overall experience"
]
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


system_prompt = f"""you calssify the review for a food delivery app.
    for the review given return
    - sentiment: positive, negative, neutral
    - sentiment_score: between -1.0 and 1.0, where -1.0 is very negative and 1.0 is very positive
    - topics: one of {TOPICS}
    - key_issues: a short phrase 8 words or less that describes the main issue in the review
    
    reply as json in this exact format:
    
    {{
        "sentiment": "positive|negative|neutral",
        "sentiment_score": float,
        "topics": topic,
        "key_issues": "short phrase"
    }}
"""


def get_connection():
    return snowflake.connector.connect(
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
        database=os.getenv("SNOWFLAKE_DATABASE"),
        schema=os.getenv("SNOWFLAKE_SCHEMA")
    )

def create_output_table(cursor):
    cursor.execute("""
        CREATE SCHEMA IF NOT EXISTS AI""")
    cursor.execute("""CREATE OR REPLACE TABLE AI.REVIEW_ENRICHED (
        review_id STRING,
        sentiment STRING,
        sentiment_score FLOAT,
        topic STRING,
        key_issues STRING,
        model STRING,
        created_at TIMESTAMP_LTZ DEFAULT CURRENT_TIMESTAMP
    )""")

def get_reviews_to_enrich(cursor):
    cursor.execute("""
        SELECT review_id, comment
        FROM ZOMATO.STAGING.STG_REVIEWS
        WHERE review_id NOT IN (SELECT review_id FROM AI.REVIEW_ENRICHED)
        LIMIT 5
    """)
    return cursor.fetchall()

def classify_review(comment):
    response = client.models.generate_content(
        model=MODEL,
        contents=comment,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0
        )
    )

    raw_text = response.text.strip()

    print("RAW GEMINI RESPONSE:")
    print(repr(raw_text))

    # Remove Markdown JSON code fences
    if raw_text.startswith("```json"):
        raw_text = raw_text[len("```json"):].strip()

    if raw_text.endswith("```"):
        raw_text = raw_text[:-3].strip()

    return json.loads(raw_text)

def save_results(cursor,results):
    cursor.executemany("""
        INSERT INTO AI.REVIEW_ENRICHED (review_id, sentiment, sentiment_score, topic, key_issues, model)
        VALUES (%(review_id)s, %(sentiment)s, %(sentiment_score)s, %(topic)s, %(key_issues)s, %(model)s)
    """, results)  

def main():
    conn = get_connection()
    cursor = conn.cursor()
    create_output_table(cursor)
    reviews = get_reviews_to_enrich(cursor)
    if not reviews:
        print("No new reviews to enrich.")
        return
    results = []
    for review_id, comment in reviews:
        try:
            classification = classify_review(comment)
        except Exception as e:
            print(f"Error occurred while classifying review {review_id}: {e}")
            continue
        results.append({
            "review_id": review_id,
            "sentiment": classification["sentiment"],
            "sentiment_score": classification["sentiment_score"],
            "topic": classification["topics"],
            "key_issues": classification["key_issues"],
            "model": MODEL
        })
    
    save_results(cursor, results)
    conn.commit()
    cursor.close()
    conn.close()
if __name__ == "__main__":
    main()