
import streamlit as st
import os
import sqlite3
import pandas as pd
import anthropic
from pathlib import Path

# Load Claude API key
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")
client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)

# Constants
DB_PATH = Path(__file__).parent.parent / "data" / "petrosila.db"
ERROR_MESSAGE = "I don't have this information. I will ask Engineer Abdelrahman; he is the one who created me and get back to you."

prompt = [
    """
    You are an expert SQL query generator specializing in the oil and gas industry. Your job is to convert natural language questions into syntactically correct SQL queries based on the following database schema. **Note:** The underlying database is SQLite, so please use SQLite-compatible syntax and date functions.
    **Important Instruction**: Return ONLY the raw SQL query as a single SELECT statement. Do NOT include any explanations, narrative, code fences (```), or additional text. Do NOT wrap the query in any formatting. The output must be the exact SQL query ready to execute.

    The database contains these tables:
    1. header_id (Fact Table): Contains core well information.
       - Columns: well_zone, well_bore, zone, field, xcord, ycord, alias, type
    2. daily_production: Contains daily production data.
       - Columns: well_zone, date, net_oil, water, gas, run_time
    3. daily_injection: Contains daily injection data.
       - Columns: well_zone, date, inj_rate, whp, run_time
    4. fluid_level: Contains daily fluid level measurements.
       - Columns: well_zone, date, pip, whp, sl, spm, pint, hz, nlap
    **Note:** The column "pip" may also be referred to as "pressure", and "nlap" may also be referred to as "dfl" by users.

    ### Special Instructions:
    1. For requests about table structure, use this pattern: SELECT name FROM sqlite_master WHERE type='table';
    2. For column listings, use: PRAGMA table_info(table_name);
    3. For injector wells, use quotes around string values: SELECT well_bore FROM header_id WHERE type = 'WI'
    4. For date filtering, use SQLite date functions (e.g. date('now') or date('now', '-1 day')).
    5. Use JOIN operations as needed, especially joining daily_production with header_id using well_zone.
    6. When aggregating production data, use proper grouping and aggregation functions.
    7. Use proper aliasing for tables when needed for clarity.
    8. **Important:** For queries that require counting unique wells (for example, counting unique well_bores for daily production that have oil production greater than 0), you must join the daily_production table with the header_id table on the well_zone column. Then, select the well_bore column from header_id. For instance, if a user asks: "Count the number of unique wells today that have production oil greater than 0", the query should be similar to:
       SELECT COUNT(DISTINCT hp.well_bore) AS unique_well_bores
       FROM daily_production dp
       JOIN header_id hp ON dp.well_zone = hp.well_zone
       WHERE dp.date = date('now') AND dp.net_oil > 0;
    9. Use JOIN operations as needed, especially joining daily_injection with header_id using well_zone

    ### Examples:
    1. **Count the number of unique wells in the database.**
       Expected Query: SELECT COUNT(DISTINCT well_zone) FROM header_id;
    2. **Retrieve daily oil production for all wells in January 2024, including well_bore and zone information.**
       Expected Query: SELECT hp.well_zone, hp.well_bore, hp.zone, dp.date, dp.net_oil
                      FROM daily_production dp
                      JOIN header_id hp ON dp.well_zone = hp.well_zone
                      WHERE dp.date BETWEEN '2024-01-01' AND '2024-01-31';
    3. **Show production total for yesterday for field se gendi.**
       Expected Query: SELECT SUM(dp.net_oil) AS total_production
                      FROM daily_production dp
                      JOIN header_id hp ON dp.well_zone = hp.well_zone
                      WHERE dp.date = date('now', '-1 day') AND hp.field = 'Se Gendi';
    4. **Show total injection by field.**
       Expected Query: SELECT hp.field, SUM(di.inj_rate) AS total_injection
                      FROM daily_injection di
                      JOIN header_id hp ON di.well_zone = hp.well_zone
                      GROUP BY hp.field;
    5. **Show total lifetime production.**
       Expected Query: SELECT SUM(net_oil) AS total_production FROM daily_production;
    6. **producer wells**
       Expected Query: SELECT well_bore FROM header_id WHERE type = 'producer';
    7. **injector wells**
       Expected Query: SELECT well_bore FROM header_id WHERE type = 'WI';
    """
]

# Generate SQL using Claude
def get_claude_response(question, prompt):
    try:
        message = client.messages.create(
            model="claude-3-5-sonnet-20240620",
            max_tokens=2000,
            temperature=0.2,
            messages=[
                {"role": "user", "content": f"{prompt[0]}\n\nQuestion: {question}"}
            ]
        )
        sql = message.content[0].text.strip()
        sql = sql.replace("```", "").replace("sql", "").replace("SQL", "").strip()
        sql = sql.replace("ite_master", "sqlite_master")
        print("🧠 Claude SQL:", sql)
        return sql
    except Exception as e:
        st.error(f"❌ Claude Error: {e}")
        return None

# Execute SQL
def read_sql_query(sql, db_path):
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute(sql)
        rows = cur.fetchall()
        cols = [desc[0] for desc in cur.description]
        conn.close()
        return cols, rows
    except sqlite3.Error as e:
        return str(e)

# Validate generated SQL
def validate_sql(query):
    forbidden_keywords = ["DROP", "DELETE", "INSERT", "UPDATE", "ALTER"]
    return not any(word in query.upper() for word in forbidden_keywords)

# UI

st.title("🛢️ Your SQL Assistant")
st.markdown(
    "Ask questions like: `Show total oil production for January 2024.`  \n"
    "**Remember** to add **'total'** if you want cumulative results."
)


col1, col2 = st.columns([3, 2])
with col1:
    question = st.text_area("Enter your question:", height=150)
    submit = st.button("🚀 Generate SQL", use_container_width=True)
    error_placeholder = st.empty()

if submit:
    with st.spinner("Thinking..."):
        sql = get_claude_response(question, prompt)

        if not sql or not validate_sql(sql):
            error_placeholder.error(ERROR_MESSAGE)
            st.stop()

        with col2:
            st.subheader("Generated SQL")
            st.code(sql, language="sql")

        result = read_sql_query(sql, DB_PATH)

        if isinstance(result, str):
            st.error("❌ SQL Execution Error:")
            st.code(sql, language="sql")
            error_placeholder.error(result)
            st.stop()

        columns, rows = result
        df = pd.DataFrame(rows, columns=columns)

        st.subheader("📊 Query Results")
        h1,h2,h3 = st.columns([1,1,1])
        with h1:
            st.dataframe(df, height=400, use_container_width=True)

        st.subheader("📈 Quick Stats")
        stats = st.columns(4)
        stats[0].metric("Total Records", len(df))
        stats[1].metric("Columns", len(df.columns))
        stats[2].metric("Numeric Columns", len(df.select_dtypes(include='number').columns))
        stats[3].metric("Unique Wells", df['well_zone'].nunique() if 'well_zone' in df.columns else "N/A")

with st.expander("💡 Example Questions"):
    st.markdown("""
    - Show total oil production for January 2024  
    - List wells with gas production above 1000  
    - Show yesterday's injection by field  
    - Count unique producers  
    - Display average water production by zone  
    """)
