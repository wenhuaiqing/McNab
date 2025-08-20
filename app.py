import streamlit as st
import os
import pandas as pd
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
import google.generativeai as genai

load_dotenv()

# print([m.name for m in genai.list_models()])

try:
    api_key = os.getenv("GOOGLE_API_KEY")

    if not api_key:
        raise ValueError("GOOGLE_API_KEY environment variable is not set.")
    genai.configure(api_key=api_key)
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite", temperature=0)
except Exception as e:
    st.error(f"Failed to initialize Gemini API. Please check your .env file. Error: {e}")
    st.stop()

# This is the "knowledge base" that the LLM will use to answer questions.
# In a real-world scenario, this would come from a database (e.g., Snowflake,
# as mentioned in the job description). This is a simplified version to
# demonstrate the concept.
project_data = {
    "Project Name": "Brisbane CBD Skyscraper",
    "Project ID": "BRS-101",
    "Status": "On Schedule",
    "Overall Progress": "75%",
    "Budget": "$500,000,000",
    "Spent to Date": "$375,000,000",
    "Key Milestones": {
        "Foundation Completed": "2025-06-30",
        "Structural Frame Topped Out": "2026-03-15",
        "Exterior Cladding Finished": "2026-10-30 (Expected)",
        "Interior Fit-out Commenced": "2026-11-01 (Expected)",
        "Final Handover": "2027-06-15 (Expected)"
    },
    "Recent Activities": [
        {"date": "2025-08-18", "activity": "Completed installation of facade panels on floors 15-20."},
        {"date": "2025-08-19", "activity": "Began interior framing on floor 12."},
        {"date": "2025-08-20", "activity": "Inspected and approved electrical rough-in on floor 10."}
    ],
    "Safety Incidents": "No major incidents reported this week. One minor cut recorded on Tuesday.",
    "Data Source": "Real-time feeds from site management, financial systems, and project schedules.",
}

# Convert complex data to a string format for the LLM prompt.
data_string = pd.DataFrame.from_dict(
    {k: [v] for k, v in project_data.items()
     if not isinstance(v, (dict, list)) and k not in ["Safety Incidents", "Data Source"]}
).to_string(index=False)

data_string += "\n\nKey Milestones:\n" + "\n".join([f"- {k}: {v}" for k, v in project_data['Key Milestones'].items()])
data_string += "\n\nRecent Activities:\n" + "\n".join([f"- {item['date']}: {item['activity']}" for item in project_data['Recent Activities']])
data_string += f"\n\nSafety Incidents:\n{project_data['Safety Incidents']}"
data_string += f"\n\nSource of Data:\n{project_data['Data Source']}"

st.set_page_config(page_title="McNab Project Report Assistant", page_icon=":construction:")

st.title("🏗️ Project Report Assistant")
st.markdown(
    "Get an instant project overview or ask the AI assistant for more details below."
)

# ------------------------------------------------------------------------------
# New Section: Visual Reports
# ------------------------------------------------------------------------------
st.header("📊 Project Overview Dashboard")

col1, col2, col3 = st.columns(3)

# Display Key Performance Indicators (KPIs)
with col1:
    st.metric(
        label="Project Status",
        value=project_data["Status"],
        delta="On Schedule" if project_data["Status"] == "On Schedule" else "Delayed"
    )

with col2:
    st.metric(
        label="Overall Progress",
        value=project_data["Overall Progress"]
    )

with col3:
    # Convert string to float for calculations
    budget_value = float(project_data["Budget"].replace("$", "").replace(",", ""))
    spent_value = float(project_data["Spent to Date"].replace("$", "").replace(",", ""))
    
    st.metric(
        label="Budget vs. Spend",
        value=f"${spent_value:,.0f}",
        delta=f"Remaining: ${budget_value - spent_value:,.0f}"
    )

st.subheader("Financial Breakdown")

# Determine the color for the "Spent to Date" bar based on a condition
spent_color = "#DC3545" if spent_value > budget_value else "#4CAF50"

# Create a simple DataFrame for the bar chart with an added color column
df_finance = pd.DataFrame({
    "Category": ["Budget", "Spent to Date"],
    "Amount": [budget_value, spent_value],
    "Color": ["#007bff", spent_color] # Neutral color for Budget, conditional color for Spent
})

# Use the new color column to dynamically color the bar chart
st.bar_chart(df_finance, x="Category", y="Amount", color="Color")

st.header("🤖 AI Report Assistant")
st.markdown(
    "Ask me a specific question about the project. For example: *'What is the project budget?'*, *'What is the overall progress?'*, or *'What is the latest activity?'*"
)

# Initialize chat history in session state
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages from history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Accept user input
if prompt := st.chat_input("Ask a question about the project..."):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    # Display user message in chat message container
    with st.chat_message("user"):
        st.markdown(prompt)

    # Generate the LLM prompt with the project context
    llm_prompt = f"""
    You are a helpful and experienced Business Intelligence Analyst for a large construction company. Your task is to analyze project data and provide clear, concise, and professional summaries or answers to questions.

    Here is the project data you must use:
    ---
    {data_string}
    ---

    Based on the data provided, answer the following question in a friendly and professional tone. If you don't know the answer based on the data, state that you cannot find the information. Avoid making up details.

    User Question: {prompt}
    """

    with st.spinner("Generating response..."):
        try:
            # Call the LLM with the formatted prompt
            response = llm.invoke(llm_prompt)
            full_response = response.content
            
            # Display assistant response in chat message container
            with st.chat_message("assistant"):
                st.markdown(full_response)
            
            # Add assistant response to chat history
            st.session_state.messages.append({"role": "assistant", "content": full_response})

        except Exception as e:
            error_message = f"An error occurred while calling the LLM. Please check your API key, endpoint, and deployment name. Error: {e}"
            st.error(error_message)
            st.session_state.messages.append({"role": "assistant", "content": error_message})
            with st.chat_message("assistant"):
                st.markdown(error_message)