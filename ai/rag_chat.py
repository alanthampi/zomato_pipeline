import os 
from google import genai
import numpy as np
import pandas as pd
import streamlit as st
import snowflake.connector
from dotenv import load_dotenv
import whisper

load_dotenv()

SYSTEM_PROMPT = """
You are an AI-powered **Zomato Review Analysis Assistant**. Your job is to answer questions about restaurant customer reviews using the review data retrieved from the database.

The reviews are enriched using AI and stored in the `ZOMATO.AI.REVIEW_ENRICHED` table. The original customer review comments are stored in `ZOMATO.STAGING.STG_REVIEWS`.

The review data may contain the following information:

* `review_id`: Unique identifier of the review.
* `comment`: Original customer review text.
* `sentiment`: The overall sentiment of the review, such as positive, negative, or neutral.
* `sentiment_score`: A numerical score representing the sentiment of the review.
* `topic` or `topics`: The topic or topics discussed in the review.
* `key_issues`: Important issues, complaints, or highlights identified from the review.
* `model`: The AI model used to enrich the review.

## Your responsibilities

1. **Answer questions using the retrieved review data.**

   Use the review comments and AI-generated enrichment fields to answer questions about customer opinions, sentiment, topics, complaints, and positive experiences.

2. **Provide accurate and evidence-based answers.**

   Use only the reviews and enrichment information provided in the context. Do not invent reviews, restaurants, customer opinions, sentiment labels, or statistics.

3. **Analyze customer sentiment.**

   When asked about sentiment, identify positive, negative, and neutral opinions based on the available enrichment data and original review text.

4. **Identify common topics and issues.**

   When asked about complaints or recurring problems, examine the `topic` and `key_issues` fields, and verify the findings against the original review comments when possible.

5. **Summarize customer feedback.**

   When asked for a summary, provide a concise overview of the main opinions, positive experiences, complaints, and recurring themes found in the retrieved reviews.

6. **Answer analytical questions carefully.**

   For questions involving counts, percentages, comparisons, or trends, calculate results only from the retrieved data. Clearly state the number of reviews analyzed and explain when the available reviews may not represent the entire review dataset.

7. **Handle insufficient information honestly.**

   If the retrieved reviews do not contain enough information to answer a question, say so clearly. Do not assume that the retrieved reviews represent all Zomato reviews.

8. **Distinguish between review facts and interpretations.**

   Clearly separate what customers explicitly said from conclusions inferred from the review data. AI-generated enrichment may contain errors, so prioritize the original review comments when there is a conflict.

9. **Protect customer privacy.**

   Do not attempt to identify customers or infer sensitive personal information from their reviews. Discuss only information relevant to the review analysis.

## Response guidelines

* Be clear, concise, and professional.
* Answer the user's question directly.
* Use bullet points or tables when they make the answer easier to understand.
* When appropriate, include review IDs as references to the supporting reviews.
* Do not mention database implementation details unless the user asks about them.
* Do not claim to have analyzed reviews that were not included in the retrieved context.
* Do not generate SQL queries unless the user explicitly asks for SQL.

## Context handling

The user question will be accompanied by reviews retrieved from the database. Treat the retrieved reviews as the context for your answer.

The context may contain original review comments and AI-generated enrichment fields. Use the following format conceptually:

REVIEW CONTEXT:

* Review ID: Unique review identifier
* Original Comment: Customer's original review
* Sentiment: AI-generated sentiment
* Sentiment Score: AI-generated sentiment score
* Topics: AI-generated topics
* Key Issues: AI-generated issues or highlights

Use this context to answer the user's question.

If no relevant reviews are provided, explain that there is insufficient review data to answer the question reliably.

**Important:** You are a review analysis assistant, not a general-purpose chatbot. Keep your answers focused on the available Zomato review data. Do not fabricate information or present unsupported conclusions as facts.

"""
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL")
CHAT_MODEL = "gemini-3.6-flash"
NEW_REVIEWS = 10
TOK_K = 5
CACHE_FILE = "review_embeddings_cache.parquet"
#modifying the secret api key to work with streamlit cloud
client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

st.title("chat with zomato reviews")
st.caption(f"searching for the top {NEW_REVIEWS} reviews based on your query with {CHAT_MODEL} chatmodel")



# function to get snowflake connection
def get_connection():
    return snowflake.connector.connect(
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
        database=os.getenv("SNOWFLAKE_DATABASE"),
        schema=os.getenv("SNOWFLAKE_SCHEMA")
    )




#fucntion to embed text using the embedding model
def embed_text(text):
    result = client.models.embed_content(
        model="gemini-embedding-2",
        contents= text
)
    return list(result.embeddings[0].values)



#function to compute cosine similarity between two vectors
def cosine_similarity(vec1, vec2):
    return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))


@st.cache_data()
def load_reviews():
    if os.path.exists(CACHE_FILE):
        review_df = pd.read_parquet(CACHE_FILE)
    else:
        cursor = get_connection().cursor()
        cursor.execute(f"""
            SELECT review_id, comment, city, rating 
            FROM ZOMATO.STAGING.STG_REVIEWS
            SAMPLE ({NEW_REVIEWS} ROWS)
            WHERE comment IS NOT NULL;
        """)
        rows = cursor.fetchall()
        get_connection().close()
        review_df = pd.DataFrame(rows, columns=["review_id", "comment", "city", "rating"])
        # Generate embeddings for the reviews
        review_df["embedding"] = review_df["comment"].apply(embed_text)
        # Save to cache file
        review_df.to_parquet(CACHE_FILE, index=False)
        print("embeddings", review_df["embedding"].head(20))
    return review_df

# get the top k reviews based on the cosine similarity to the query embedding
def get_top_k_reviews(question,review_df, k=TOK_K):
    query_embedding = embed_text(question)
    review_df["similarity"] = review_df["embedding"].apply(lambda x: cosine_similarity(query_embedding, x))
    top_k_reviews = review_df.nlargest(k, "similarity")
    return top_k_reviews[["review_id", "comment", "city", "rating", "similarity"]]




# llm model to asak your question to about the reviews
def ask_llm(question, context):
    context = context.to_json(orient="records")
    prompt = f"REVIEW CONTEXT:\n{context}\n\nQUESTION: {question}\n\n"
    response = client.models.generate_content(
        model=CHAT_MODEL,
        contents=prompt,
        config=genai.types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.2
        )
    )
    return response.text.strip()






@st.cache_resource
def load_model():
    return whisper.load_model("base")


def main():

    st.title("🎤 Zomato Review Assistant")

    # -------------------------------
    # Load Whisper model
    # -------------------------------

    model = load_model()

    # -------------------------------
    # Audio Input
    # -------------------------------

    st.subheader("note the table that is being queried is not full enriched by the due to budget limitation only 5 rows are done")

    audio_value = st.audio_input("Record your question")

    voice_question = ""

    if audio_value:

        # Save recorded audio
        with open("recording.wav", "wb") as f:
            f.write(audio_value.getvalue())

        # Transcribe audio using Whisper
        result = model.transcribe("recording.wav")

        voice_question = result["text"].strip()

        st.write("**Transcription:**")
        st.write(voice_question)

    # -------------------------------
    # Text Input
    # -------------------------------

    st.subheader("⌨️ Or type your question")

    text_question = st.text_input(
        "Enter your question about Zomato reviews:",
        placeholder="e.g., What are the common complaints about food quality?"
    )

    # -------------------------------
    # Decide which question to use
    # -------------------------------

    if voice_question:
        question = voice_question
    else:
        question = text_question

    # -------------------------------
    # Process Question
    # -------------------------------

    if question.strip():

        review_df = load_reviews()

        top_k_reviews = get_top_k_reviews(
            question,
            review_df
        )

        answer = ask_llm(
            question,
            top_k_reviews
        )

        st.markdown("### Answer")

        st.write(answer)

        st.markdown("### Relevant Reviews")

        st.dataframe(top_k_reviews)


if __name__ == "__main__":
    main()

