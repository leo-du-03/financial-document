import streamlit as st
import pandas as pd
from src.answer import answer
import plotly.express as px
import json

def get_context():
    recent_messages = current_chat.tail(3)
    context = ""
    for index, row in recent_messages.iterrows():
        context += f"Query: {row['query']} \nResponse: {row['response']}\n==========================\n"
    return context

# == PAGE CONFIGURATION ==
st.set_page_config(
    page_title="Financial Document Question Answering System",
)
with open("style.css") as css:
    st.markdown(f"<style>{css.read()}</style>", unsafe_allow_html=True)

# Initialize session state if not already present
if "chats" not in st.session_state:
    st.session_state["chats"] = {"0": pd.DataFrame({"query": [], "response": []})}
if "chat_counter" not in st.session_state:
    st.session_state["chat_counter"] = 1
if "current_chat_id" not in st.session_state:
    st.session_state["current_chat_id"] = "0"
if "past_queries" not in st.session_state:
    st.session_state["past_queries"] = []

current_chat_id = st.session_state["current_chat_id"]
current_chat = st.session_state["chats"][current_chat_id]

# Streamlit UI
st.title("Financial Document Question Answering System")

# User Interface Section
with st.chat_message("program"):
    query = st.chat_input("Enter your query:", key="query")

with st.popover("⚠️"):
    st.markdown(
        """
    **Please Note:**
    
    Questions should only be asked about public companies that are registered with the U.S. Securities and Exchange Commission (SEC). 
    
    Queries about non-registered companies may fail or produce inaccurate results.
    """
    )

if query:
    if query.strip() == "":
        st.warning("Please enter a query.")
    else:
        response, classification = answer(query, current_chat_id, get_context())

        if response:
            if isinstance(response, str):
                if response.startswith("Error processing query:"):
                    # Display error in an error box
                    st.error(response, icon="🚨")
                else:
                    current_chat.loc[len(current_chat)] = [query, response] #slices data set length into query and response
                    st.session_state["chats"][current_chat_id] = current_chat #sets this current chat
                    st.session_state["past_queries"].append((query, response))
                    with st.chat_message(
                        "program"
                    ):
                        st.subheader("Response:")
                        st.write(response)
            else:
                if classification == "visualization":
                    try:
                        viz_data = response
                        if viz_data["chart_type"] == "line":
                            fig = px.line(
                                x=viz_data["data"]["x"],
                                y=viz_data["data"]["y"],
                                title=viz_data["title"],
                            )
                        elif viz_data["chart_type"] == "bar":
                            fig = px.bar(
                                x=viz_data["data"]["x"],
                                y=viz_data["data"]["y"],
                                title=viz_data["title"],
                            )
                        elif viz_data["chart_type"] == "scatter":
                            fig = px.scatter(
                                x=viz_data["data"]["x"],
                                y=viz_data["data"]["y"],
                                title=viz_data["title"],
                            )
                        elif viz_data["chart_type"] == "pie":
                            fig = px.pie(
                                values=viz_data["data"]["y"],
                                names=viz_data["data"]["x"],
                                title=viz_data["title"],
                            )
                        elif viz_data["chart_type"] == "area":
                            fig = px.area(
                                x=viz_data["data"]["x"],
                                y=viz_data["data"]["y"],
                                title=viz_data["title"],
                            )
                        else:
                            st.error("Unsupported chart type")

                        fig.update_layout(
                            xaxis_title=viz_data["x_axis"],
                            yaxis_title=viz_data["y_axis"],
                        )
                        st.plotly_chart(fig, use_container_width=True)
                        response = json.dumps(response)
                        current_chat.loc[len(current_chat)] = [query, response] #slices data set length into query and response
                        st.session_state["chats"][current_chat_id] = current_chat #sets this current chat
                        st.session_state["past_queries"].append((query, response))
                    except json.JSONDecodeError:
                        st.error("Failed to parse visualization data")
        else:
            st.error("No response received. Please check your query and try again.")
else:
    st.error("Please enter a query.")

st.subheader("Past Queries and Responses:")
if st.session_state["past_queries"]:
    for idx, (q, r) in enumerate(st.session_state["past_queries"]):
        st.markdown(f"**Query {idx + 1}:** {q}")
        st.markdown(f"**Answer:** {r}")
        st.markdown("---")
else:
    st.info("No past queries yet.")

# Load previous chat stats
def load_chat(chat_id):
    st.session_state["current_chat_id"] = chat_id
    st.session_state["past_queries"] = [
        (query, response)
        for query, response in zip(
            st.session_state["chats"][chat_id]["query"],
            st.session_state["chats"][chat_id]["response"],
        )
    ]

def start_new_chat():
    new_chat_id = str(st.session_state["chat_counter"])
    st.session_state["chats"][new_chat_id] = pd.DataFrame({"query": [], "response": []})
    st.session_state["chat_counter"] += 1
    st.session_state["current_chat_id"] = new_chat_id
    st.session_state["past_queries"] = []

def convert_df(df):
    # IMPORTANT: Cache the conversion to prevent computation on every rerun
    return df.to_csv().encode("utf-8")

def flatten_chats(chats):
    flattened = pd.DataFrame({"query": [], "response": []})
    for chat in chats.values():
        flattened = pd.concat([flattened, chat], ignore_index=True)
    return flattened.to_csv().encode("utf-8")

chat_csv = convert_df(current_chat)
all_chat_csv = flatten_chats(st.session_state["chats"])

# Sidebar for chat management
with st.sidebar:
    st.subheader("Download current chat history")
    st.download_button(
        label="Download current chat history as CSV",
        data=chat_csv,
        file_name=f"{current_chat_id}_chat_history.csv",
        mime="text/csv"
    )

    st.subheader("Download all chat history")
    st.download_button(
        label="Download all chat history as CSV",
        data=all_chat_csv,
        file_name="chat_history.csv",
        mime="text/csv"
    )

    st.subheader("Create Chat")
    if st.button("New Chat"):
        start_new_chat()
        st.rerun()  # Refreshes page

    st.subheader("Load Previous Chats")
    for chat in st.session_state["chats"].keys():
        if st.button(f"Load Chat {chat}"):
            load_chat(chat)
            st.rerun() #refreshes page
