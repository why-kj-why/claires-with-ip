import streamlit as st

NLTK_DATA = "./nltk_data"
# TIKTOKEN_DATA = "./tiktoken_cache"

from llama_index.llms.azure_openai import AzureOpenAI
from pandas import DataFrame
from pymysql import connect
from requests import post

# database credentials
DB_HOST = "tellmoredb.cd24ogmcy170.us-east-1.rds.amazonaws.com"
DB_USER = "admin"
DB_PASS = "2yYKKH8lUzaBvc92JUxW"
DB_PORT = "3306"
# DB_NAME = "claires_data"
DB_NAME = "retail_panopticon"
CONVO_DB_NAME = "store_questions"

# TellMore IP endpoint
# API_URL = "http://127.0.0.1:5000/response"
API_URL = "http://tellmore-ip.azurewebsites.net/api/response"

# TellMore Azure OpenAI credentials
AZURE_OPENAI_KEY = "94173b7e3f284f2c8f8eb1804fa55699"
AZURE_OPENAI_ENDPOINT = "https://tellmoredemogpt.openai.azure.com/"
AZURE_OPENAI_ENGINE = "tellmore-demo-gpt35"
AZURE_OPENAI_MODEL_NAME = "gpt-3.5-turbo-0125"
AZURE_OPENAI_TYPE = "azure"

# Claire's Accessories' colours
CLAIRE_DEEP_PURPLE = "#553D94"
CLAIRE_MAUVE = "#D2BBFF"

# AzureOpenAI LLM setup
llm = AzureOpenAI(
    model=AZURE_OPENAI_MODEL_NAME,
    engine=AZURE_OPENAI_ENGINE,
    api_key=AZURE_OPENAI_KEY,
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    api_type=AZURE_OPENAI_TYPE,
    api_version="2024-03-01-preview",
    temperature=0.3,
)

# session state variables
if 'history' not in st.session_state:
    st.session_state['history'] = []

if 'display_df_and_nlr' not in st.session_state:
    st.session_state['display_df_and_nlr'] = False

if 'user_input' not in st.session_state:
    st.session_state['user_input'] = ""


# connection to database
def connect_to_db(db_name):
    return connect(
        host = DB_HOST,
        port = int(DB_PORT),
        user = DB_USER,
        password = DB_PASS,
        db = db_name
    )


# post business query to TellMore IP
def send_message_to_api(message):
    api_url = API_URL
    payload = {
        "database": DB_NAME,
        "query": message
    }
    response = post(api_url, json = payload)
    if response.status_code == 200:
        try:
            return response.json()
        except ValueError:
            st.error("Error decoding JSON")
            return None
    else:
        st.error(f"Error: HTTP {response.status_code} - {response.text}")
        return None


# execute SQL query
def execute_query(query, connection):
    try:
        with connection.cursor() as cursor:
            cursor.execute(query)
            getResult = cursor.fetchall()
            columns = [column[0] for column in cursor.description]
        return DataFrame(getResult, columns = columns)
    finally:
        connection.close()


# store business query
def store_question_in_db(question, sql_query):
    connection = connect_to_db(CONVO_DB_NAME)
    query = "INSERT INTO pinned_questions (question, sql_query) VALUES (%s, %s)"
    try:
        with connection.cursor() as cursor:
            cursor.execute(query, (question, sql_query))
        connection.commit()
    finally:
        connection.close()


# retrieve business queries
def get_queries_from_db():
    connection = connect_to_db(CONVO_DB_NAME)
    query = "SELECT DISTINCT question, sql_query FROM pinned_questions;"
    df = execute_query(query, connection)
    questions = {"Select a query": None}
    questions.update(dict(zip(df['question'], df['sql_query'])))
    return questions


# custom CSS for Streamlit app
def set_custom_css():
    custom_css = """
    <style>
        .st-emotion-cache-9aoz2h.e1vs0wn30 {
            display: flex;
            justify-content: center; /* Center-align the DataFrame */
        }
        .st-emotion-cache-9aoz2h.e1vs0wn30 table {
            margin: 0 auto; /* Center-align the table itself */
        }

        .button-container {
            display: flex;
            justify-content: flex-end; /* Align button to the right */
            margin-top: 10px;
        }

        .circular-button {
            border-radius: 50%;
            background-color: #553D94; /* Button color */
            color: white;
            border: none;
            padding: 10px 15px; /* Adjust size as needed */
            cursor: pointer;
        }

        .circular-button:hover {
            background-color: #452a7f; /* Slightly darker shade on hover */
        }
    </style>
    """
    st.markdown(custom_css, unsafe_allow_html=True)


# Store Ops application
def store_ops_app():
    with open(r'claires-logo.svg', 'r') as image:
        image_data = image.read()
    st.logo(image=image_data)

    st.markdown(f"""
    <h4 style="background-color: {CLAIRE_DEEP_PURPLE}; color: white; padding: 10px;">
        Ask a Question
    </h4>
    """, unsafe_allow_html=True)

    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

    st.markdown("""
    <style>
    div.stButton {
        display: flex;
        justify-content: flex-end; /* Align button to the right */
        font-size: 30px; /* Increase font size */
        margin-top: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

    save_button_pressed = st.button('### :material/save:', key='save_button')

    if save_button_pressed:
        if st.session_state.history:
            last_chat = st.session_state.history[-1]
            store_question_in_db(last_chat['question'], last_chat['sql'])
            st.success("Last conversation stored.")
            st.session_state['user_input'] = ""
            st.session_state['display_df_and_nlr'] = False
            st.session_state['last_result'] = None
            st.session_state['last_nlr'] = None
        else:
            st.warning("No conversation to store.")

    for chat in st.session_state.history:
        st.write(f"**User:** {chat['question']}")
        st.write(f"**Natural Language Response:** {chat['nlr']}")

    st.session_state['user_input'] = st.text_input("Business Question: ", st.session_state['user_input'])

    if st.session_state['user_input'] and not save_button_pressed:
        ip_response = send_message_to_api(st.session_state['user_input'])
        st.session_state.history.append({
            "question": st.session_state['user_input'],
            "nlr": ip_response["Engine Response"],
            "sql": ip_response["Query SQL"],
        })
        conn = connect_to_db(DB_NAME)
        result = execute_query(ip_response["Query SQL"], conn)
        st.session_state['display_df_and_nlr'] = True
        st.session_state['last_result'] = result
        st.session_state['last_nlr'] = st.session_state.history[-1]["nlr"]

    if st.session_state['display_df_and_nlr']:
        st.dataframe(st.session_state['last_result'], height = 200)
        st.write(st.session_state['last_nlr'])


# Store Manager application
def store_manager_app():
    with open(r'claires-logo.svg', 'r') as image:
        image_data = image.read()
    st.logo(image=image_data)

    store_list = ["Store ID", "STORE01", "STORE20", "STORE38"]

    store_questions = get_queries_from_db()

    if 'queries' not in st.session_state:
        st.session_state["queries"] = {
            store_list[0]: {"Select a query": None},
            store_list[1]: store_questions,
            store_list[2]: store_questions,
            store_list[3]: store_questions,
        }

    st.markdown(f"""
    <h4 style="background-color: {CLAIRE_DEEP_PURPLE}; color: white; padding: 10px;">
        Simulate a Store
    </h4>
    """, unsafe_allow_html=True)

    store_name_id_placeholder = st.markdown(f"""
    <h4 style="background-color: {CLAIRE_MAUVE}; color: black; padding: 10px;">
    </h4>
    """, unsafe_allow_html=True)

    st.markdown("""
        <style>
        div.stButton {
            display: flex;
            justify-content: flex-end; /* Align button to the right */
            font-size: 30px; /* Increase font size */
            margin-top: 10px;
        }
        </style>
        """, unsafe_allow_html=True)

    unpin_button_pressed = st.button('### :material/delete:', key='unpin_button')

    selected_store = st.selectbox("Select a Store", store_list)

    if selected_store != "Store ID":
        store_name = {
            "STORE01": "CYBERTRON",
            "STORE20": "SINNOH",
            "STORE38": "TATOOINE"
        }.get(selected_store, "")

        store_name_id_placeholder.markdown(f"""
        <h4 style="background-color: {CLAIRE_MAUVE}; color: black; padding: 10px;">
            {store_name}, {selected_store}
        </h4>
        """, unsafe_allow_html=True)

    queries_for_store = st.session_state['queries'].get(selected_store, {})
    query_options = list(queries_for_store.keys())
    selected_query = st.selectbox("Select a query", query_options if query_options else ["Select a query"])

    if unpin_button_pressed:
        if selected_query != "Select a query":
            queries_for_store.pop(selected_query, None)
            st.session_state['queries'][selected_store] = queries_for_store
            st.success(f"Query '{selected_query}' has been removed.")
        else:
            st.warning("Select a query to unpin.")

    if selected_store and selected_store != "Store ID" and selected_query and selected_query != "Select a query" and not unpin_button_pressed:
        conn = connect_to_db(DB_NAME)
        cur = conn.cursor()
        cur.execute(st.session_state["queries"][selected_store][selected_query])
        getDataTable = cur.fetchall()
        language_prompt = f"""
            following is a business question: {selected_query}\n
            columns from an enterprise database schema were identified to answer this question\n
            upon querying the columns, the following SQL data table was returned: {getDataTable}\n
            generate a natural language response explaining the data table that was 
            returned, with the business question as context\n
            respond only with the natural language explanation of the data table output, do not explain the 
            business question or how the columns were selected and queried\n
        """
        ans = llm.complete(language_prompt).text
        st.markdown(ans)


# main application setup
set_custom_css()
st.set_page_config(layout = 'wide', initial_sidebar_state = 'collapsed')  # wide mode
persona = st.sidebar.radio("", ("Ask a Question", "Simulate a Store"))  # sidebar toggle

if persona == "Ask a Question":
    store_ops_app()

elif persona == "Simulate a Store":
    store_manager_app()
