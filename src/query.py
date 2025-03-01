import json
import shutil
import streamlit as st
import regex as re
from datetime import datetime
from llama_index.core import (
    VectorStoreIndex,
    SimpleDirectoryReader,
    StorageContext,
    load_index_from_storage
)

classification_prompt = """
You are an expert financial assistant tasked with examining and categorizing a financial question. 
You will categorize the query type.
Instructions:
1. Read the financial question carefully.
2. Categorize the query into one of the following types:
   - Text: Questions answered in text format (e.g., general information queries)
   - Arithmetic: Questions involving mathematical calculations
   - Visualization: Questions requiring data to be presented in graphs
3. Provide only the type as a single word, without any additional text or explanation.

User Query: {query}
"""

visualization_prompt = """
You are an expert data visualization assistant. Analyze the given financial query and produce a JSON structure describing an appropriate visualization to answer the query, compatible with Streamlit and Plotly.

Instructions:
1. Read the financial question carefully.
2. Determine the most suitable visualization type to represent the data that would answer the query.
3. Create a JSON structure with the following elements:
   - chart_type: The type of chart (e.g., "line", "bar", "scatter", "pie", "area")
   - title: A descriptive title for the chart
   - x_axis: Description of the x-axis (typically time periods)
   - y_axis: Description of the y-axis (typically financial metrics)
   - data: A dictionary containing:
     - x: List of x-axis values
     - y: List of y-axis values (or list of lists for multiple series)
   - options: A dictionary containing any additional options for the chart

4. Return only the JSON structure as a string, without any additional text or explanation.

User Query: {query}
"""

persist_dir = {}

def get_response(folder, query, class_type, ind):
    if f"{ind}" in persist_dir:
        shutil.rmtree(f"{persist_dir[f'{ind}']}")

    persist_dir[f"{ind}"] = f"{folder}_storage"
    dir = f"{folder}_storage"

    class_type = class_type.lower()

    # Ingesting documents
    with st.spinner("Ingesting documents..."):
        documents = SimpleDirectoryReader(folder).load_data()
        # analyzes the documents in the folder provided
        index = VectorStoreIndex.from_documents(documents)
        if ind is not None:
            index.storage_context.persist(persist_dir=dir)
    
    with st.spinner("Generating response..."):
        query_engine = index.as_query_engine()
        # gets the response
        if class_type == "text" or class_type == "arithmetic":
            prompt = (
                f"{query}\nPlease provide a definitive answer that directly answers the question using your general knowledge of the topic alongside the provided documents."
                f"Be as precise as possible in your language. Do not be vague."
                f"Make sure to support your answer with data points from the provided documents."
                f"The current date is {datetime.today().strftime('%Y-%m-%d')}"
            )
            response = query_engine.query(prompt)
            response = response.response
        elif class_type == "visualization":
            visualization_query = visualization_prompt.format(query=query)
            response = query_engine.query(visualization_query)
            response = response.response
            response = response[response.find("{"):]
            response = response[::-1]
            response = response[response.find("}"):]
            response = response[::-1]
            response = json.loads(response)
        else:
            raise ValueError(f"Invalid class: {class_type}")

    return response, 0
  
def get_follow_up(query, ind, context):
    if f"{ind}" in persist_dir:
        storage_context = StorageContext.from_defaults(persist_dir=persist_dir[f"{ind}"])
        index = load_index_from_storage(storage_context)
        query_engine = index.as_query_engine()

        classification_query = classification_prompt.format(query=query)
        classification = query_engine.query(classification_query).response.strip().lower()

        if classification == "visualization":
            visualization_query = visualization_prompt.format(query=query)
            response = query_engine.query(visualization_query)
            response = response.response
            response = response[response.find("{"):]
            response = response[::-1]
            response = response[response.find("}"):]
            response = response[::-1]
            response = json.loads(response)
        else:
            prompt = (
                f"{query}\nPlease provide a definitive answer that directly answers the question using your general knowledge of the topic alongside the provided documents."
                f"Be as precise as possible in your language. Do not be vague."
                f"Make sure to support your answer with data points from the documents provided.\n"
                f"Here are the last 3 queries and responses for context:\n{context}"
            )
            response = query_engine.query(prompt).response

        return response, 0, classification
    else:
        return "Please make a query before asking a follow-up question.", 0

def clear_persist():
    clicked = st.button("Clear memory of models")
    if clicked:
        for dir in persist_dir.values():
            shutil.rmtree(f"{dir}")
