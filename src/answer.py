import os
import sys
import shutil
import json
import time
import asyncio
import streamlit as st
from prisma import Prisma
from src.query import get_response, get_follow_up
from src.documents import get_documents, get_params

sys.path.append(os.path.dirname(__file__))

async def log_kpi(tokens, time, query, response, followup):
    db = Prisma()
    await db.connect()
    await db.log.create(
        {
            "tokensUsed": tokens,
            "timeSpent": time,
            "query": query,
            "response": response,
            "followup": followup,
        }
    )
    await db.disconnect()

def answer(query, index, context):
    start = time.time()
    
    if not query.lower().startswith("follow up:"):
        folder_name = ""
        try:
            # Retrieve parameters
            with st.spinner("Parsing query..."):
                params, param_tokens = get_params(query)
                print(params)

            # Extract classification from params
            classification = params.get("category", "text").lower()  # Default to "text" if not specified

            # Retrieve folder name where documents are saved
            with st.spinner("Fetching documents..."):
                folder_name = get_documents(params)

            if folder_name:
                # Get response using folder name, user query, and classification
                response, response_tokens = get_response(folder_name, query, classification, index)

                tokens = param_tokens + response_tokens
                end = time.time()
                length = end - start

                if classification == "visualization":
                    asyncio.run(log_kpi(tokens, length, query, json.dumps(response), False))
                else:
                    asyncio.run(log_kpi(tokens, length, query, response, False))

                return response, classification
            else:
                return "Failed to retrieve documents.", classification

        except Exception as e:
            return f"Error processing query: {e}", "text"
        
        finally:
            if folder_name != "" and os.path.exists(folder_name):
                shutil.rmtree(folder_name)
                print(f"Deleted folder: {folder_name}")
    else:
        # Handle follow-up queries
        with st.spinner("Generating response..."):
            response, response_tokens, classification = get_follow_up(query, index, context)

        end = time.time()
        length = end - start

        if classification == "visualization":
            asyncio.run(log_kpi(response_tokens, length, query, json.dumps(response), False))
        else:
            asyncio.run(log_kpi(response_tokens, length, query, response, False))

        return response, classification
