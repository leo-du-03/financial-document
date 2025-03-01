import requests
import os
import uuid
import time
import json
import streamlit as st
from openai import OpenAI
from datetime import datetime
from dateutil.relativedelta import relativedelta
import pdfkit
from src.download_xbrl_data import download_documents

os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]
client = OpenAI()

system_prompt = f"""
You are an expert financial assistant tasked with examining and categorizing a financial question. 
You will examine the financial question provided, and accurately extract the company or companies of interest, and provide the correct CIK (Central Index Key) for each company. You will also give a relevant timeframe that the question mentions, and categorize the query type.

The current date is {datetime.today().strftime('%Y-%m-%d')}

Instructions:
1. Carefully read the financial question provided.
2. Identify the company or companies of interest in the question.
3. For each company, provide the 10-digit CIK (Central Index Key). If you're not 100% certain, make your best educated guess based on your knowledge.
4. Determine the relevant financial quarters mentioned in the question in YYYYQ# format.
5. Categorize the query into one of the following types:
   - Text: Questions answered in text format (e.g., general information queries)
   - Arithmetic: Questions involving mathematical calculations
   - Visualization: Questions requiring data to be presented in graphs
6. Return the information in this format, extending lists as necessary:
   ciks:timeframes:category
7. Remember, the "ciks" will be the CIK (Central Index Key) numbers for the companies that the user asked about. "timeframes" is the relevant timeframe that the user will ask in the question. "category" is one of the three categories that you will organize the question into, either text, arithmetic, or visualization.

Important:
- Always provide a CIK, even if you're not 100% certain. Use your best judgment based on available information.
- Ensure the CIK format is correct: a 10-digit number starting with one or more zeros.
- Prioritize well-known, large cap companies when making educated guesses.
- If multiple companies are mentioned but you can only confidently provide CIKs for some, still include all companies in your response.

Examples:
1. Question: "How much revenue did Apple generate in Q1 2024?"
   Response: 0000320193:2024Q1:Arithmetic

2. Question: "Compare the stock prices of Microsoft and Google over the last two quarters of 2023."
   Response: 0000789019, 0001652044:2023Q3, 2023Q4:Visualization

3. Question: "Describe Amazon's expansion strategy in 2023."
   Response: 0001018724:2023Q1, 2023Q2, 2023Q3, 2023Q4:Text

4. Question: "What was Nvidia's profit margin in the first half of 2024?"
   Response: 0001045810:2024Q1, 2024Q2:Arithmetic

5. Question: "How has Tesla's stock performed compared to Ford in the last quarter?"
   Response: 0001318605, 0000037996:2024Q2:Visualization

Remember, while accuracy is crucial, it's better to provide a best guess than to omit the CIK entirely. Always strive to provide a CIK for each company mentioned, using your best judgment when necessary.
"""

form_types_prompt = """
You are an assistant tasked with determining which SEC forms are relevant for answering a financial question. 
Given the following financial question, provide a list of relevant SEC form types that would be useful for answering the question.
Instructions:
1. Carefully read the financial question provided.
2. Identify the SEC forms that would contain information that can be used to answer the question.
3. Return the information in this format, extending the list as necessary:
    form, form
"""


def ask_llm(user_prompt: str):
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        ai_response = response.choices[0].message.content
        tokens = response.usage.total_tokens
        return ai_response, tokens
    except Exception as e:
        return f"Error with getting response: {e}"


def get_relevant_form_types(user_query: str):
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": form_types_prompt},
                {"role": "user", "content": user_query},
            ],
        )
        ai_response = response.choices[0].message.content
        tokens = response.usage.total_tokens
        return [form.strip() for form in ai_response.split(",")], tokens
    except Exception as e:
        return f"Error with getting response: {e}"


def get_params(user_query):
    try:
        response, ask_tokens = ask_llm(user_query)
        parsed_result = response.split(":")

        ciks_str = parsed_result[0].strip()
        timeframes_str = parsed_result[1].strip()
        category = parsed_result[2].strip()

        ciks = [c.strip() for c in ciks_str.split(",")]
        timeframes = [t.strip() for t in timeframes_str.split(",")]

        relevant_forms, forms_tokens = get_relevant_form_types(user_query)

        total_tokens = ask_tokens + forms_tokens

        return {
            "ciks": ciks,
            "timeframes": timeframes,
            "category": category,
            "relevant_forms": relevant_forms,
        }, total_tokens
    except Exception as e:
        return {"Error": str(e)}


def get_documents(params):
    ciks = params["ciks"]
    folder_name = str(uuid.uuid4())
    os.makedirs(folder_name, exist_ok=True)
    timeframes = params["timeframes"]

    for date_param in timeframes:
        try:
            year = int(date_param[:4])
            quarter = int(date_param[5])
            start_month = (quarter - 1) * 3 + 1
            start_date = datetime(year, start_month, 1)

            get_documents_submissions(
                ciks, folder_name, start_date, params.get("relevant_forms")
            )
        except Exception as e:
            print(f"Error in getting documents: {e}")
            return None

    return folder_name


def get_documents_submissions(ciks, folder_name, start_date, relevant_forms):
    base_url = "https://data.sec.gov/submissions/CIK"
    file_path = os.path.join(folder_name, "edgar_data.json")

    for cik in ciks:
        cik_padded = cik.zfill(10)
        api_url = f"{base_url}{cik_padded}.json"
        email = st.secrets["EMAIL"]
        headers = {
            "User-Agent": f"{email}",
            "Accept-Encoding": "gzip, deflate",
            "Host": "data.sec.gov",
        }

        try:
            time.sleep(0.1)
            response = requests.get(api_url, headers=headers)
            response.raise_for_status()

            data = response.json()
            with open(file_path, "w") as f:
                json.dump(data, f, indent=4)

            # Earliest filing date from the fetched data
            if (
                "filings" in data
                and "recent" in data["filings"]
                and "filingDate" in data["filings"]["recent"]
            ):
                filing_dates = data["filings"]["recent"]["filingDate"]
                if filing_dates:
                    earliest_filing_date_str = filing_dates[-1]
                    earliest_filing_date = datetime.strptime(
                        earliest_filing_date_str, "%Y-%m-%d"
                    )

                    # Compare with start_date
                    if earliest_filing_date > start_date:
                        st.warning('SEC filings cannot be found, so answers have a greater likelihood to be inaccurate or vague.', icon="⚠️")
                        get_documents_frames(ciks, folder_name, start_date)
                    else:
                        download_edgar_files(folder_name, start_date, relevant_forms)

                        if os.path.exists(file_path):
                            os.remove(file_path)

        except requests.exceptions.RequestException as e:
            print(f"Request failed for CIK {cik}: {e}")
        except json.JSONDecodeError as e:
            print(f"JSON decode error for CIK {cik}: {e}")
        except Exception as e:
            print(f"An unexpected error occurred for CIK {cik}: {e}")

    return folder_name


def get_documents_frames(ciks, folder_name, start_date):
    base_url = "https://data.sec.gov/api/xbrl/frames"
    os.makedirs(folder_name, exist_ok=True)
    file_path = os.path.join(folder_name, "xbrl_data.json")

    for cik in ciks:
        email = st.secrets["EMAIL"]
        headers = {
            "User-Agent": f"{email}",
            "Accept-Encoding": "gzip, deflate",
            "Host": "data.sec.gov",
        }

        concepts = ["Assets", "Liabilities", "LongTermDebt", "AccountsPayableCurrent"]
        all_data = {}

        try:
            for concept in concepts:
                api_url = f"{base_url}/default/{concept}/USD/CY{start_date.year}Q{start_date.quarter}I.json"

                time.sleep(0.1)
                response = requests.get(api_url, headers=headers)
                response.raise_for_status()

                data = response.json()

                if "data" in data:
                    cik = int(str(cik).lstrip("0"))
                    filtered_data = [
                        item for item in data["data"] if item["cik"] == cik
                    ]
                    data["data"] = filtered_data

                all_data[concept] = data

            with open(file_path, "w") as f:
                json.dump(all_data, f, indent=4)

            download_documents(all_data, folder_name)

        except requests.exceptions.RequestException as e:
            print(f"Request failed for CIK {cik}: {e}")
        except json.JSONDecodeError as e:
            print(f"JSON decode error for CIK {cik}: {e}")
        except Exception as e:
            print(f"An unexpected error occurred for CIK {cik}: {e}")

    return folder_name


def download_edgar_files(folder_name, start_date, relevant_forms):
    with open(os.path.join(folder_name, "edgar_data.json"), "r") as f:
        data = json.load(f)

    recent_filings = data["filings"]["recent"]
    cik = data["cik"]
    primaryDocumentLink = recent_filings["primaryDocument"]
    start_date = start_date - relativedelta(months=3)
    end_date = start_date + relativedelta(months=6)
    filing_format = "%Y-%m-%d"

    if recent_filings.get("accessionNumber"):
        index = 0
        for accession_number in recent_filings["accessionNumber"]:
            filing_date = datetime.strptime(
                recent_filings["filingDate"][index], filing_format
            )
            if (
                (recent_filings["form"][index] in relevant_forms
                or recent_filings["form"][index] == "10-Q"
                or recent_filings["form"][index] == "10-K")
                and filing_date > start_date
                and filing_date < end_date
            ):
                try:
                    primaryDocument = primaryDocumentLink[index]
                    accession_number = "".join(accession_number.split("-"))
                    html_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession_number}/{primaryDocument}"
                    output_path = os.path.join(folder_name, f"{accession_number}.pdf")
                    pdfkit.from_url(html_url, output_path)
                except Exception as e:
                    print(f"Error: {e}")
                time.sleep(0.1)
            elif filing_date < start_date:
                break

            index += 1
    else:
        print("No recent filings found")
