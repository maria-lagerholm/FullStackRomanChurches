import os
import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine, text
from pymssql import connect

st.set_page_config(
    layout="wide",
    page_title="Roman Churches Insights",
    page_icon="⛪",
    initial_sidebar_state="collapsed"
)

# Inject custom CSS for the selectbox border
st.markdown("""
    <style>
    /* Adjust font sizes for better readability on mobile */
    @media only screen and (max-width: 600px) {
        body, .stApp {
            font-size: 14px !important;
        }
    }

    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Custom styling for the app container */
    .stApp {
        max-width: 1200px;
        margin: 0 auto;
    }

    /* Style the selectbox container */
    [data-baseweb="select"] > div {
        border: 2px solid #0067C8 !important;
        border-radius: 4px !important;
    }
    </style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------------------
# Set up secure database credentials based on environment
# ------------------------------------------------------------------------
if "AZURE_SQL_PASSWORD" in os.environ:
    # Running locally: use environment variables
    password = os.environ["AZURE_SQL_PASSWORD"]
    username = os.environ["AZURE_SQL_USERNAME"]
    server = "marialagerholm.database.windows.net"
    database = "lagerholmDB"
else:
    # Running on Streamlit Cloud: use secrets
    password = st.secrets["azure_sql"]["password"]
    username = st.secrets["azure_sql"]["username"]
    server = st.secrets["azure_sql"]["server"]
    database = st.secrets["azure_sql"]["database"]

azure_connection = f"mssql+pymssql://{username}:{password}@{server}/{database}"
engine = create_engine(azure_connection)

# ------------------------------------------------------------------------
# Figure 1: Count how many churches were built each century
# ------------------------------------------------------------------------
query_count = "SELECT built_century, COUNT(*) AS count FROM RomanChurches_Main GROUP BY built_century"
df_count = pd.read_sql_query(text(query_count), engine)

all_centuries = list(range(1, 22))
df_plot1 = pd.DataFrame({'built_century': all_centuries}).merge(
    df_count, on='built_century', how='left'
).fillna(0)

fig1 = px.bar(
    df_plot1,
    x='built_century',
    y='count',
    title='Number of Churches Built in Rome per Century',
    text='count'
)
fig1.update_layout(xaxis_title="Century", yaxis_title="Count", xaxis=dict(dtick=1))

# ------------------------------------------------------------------------
# Figure 2: Population of Rome per century (interpolated)
# ------------------------------------------------------------------------
df_pop = pd.read_sql("SELECT Century, Event, Population FROM RomanPopulation", engine)
centuries_full = pd.DataFrame({'Century': list(range(-8, 22))})
df_pop['Century'] = df_pop['Century'].astype(int)
df_pop = df_pop[df_pop['Century'] <= 21]

df_merged = centuries_full.merge(
    df_pop[['Century', 'Population']],
    on='Century', how='left'
).interpolate()

df_events = df_pop[['Century', 'Event']].dropna()
df_plot2 = df_merged.merge(df_events, on='Century', how='left')
df_plot2['Event'] = df_plot2['Event'].fillna('')
events_df = df_plot2[df_plot2['Event'] != ''].copy()
events_df['Event_ID'] = range(1, len(events_df) + 1)
df_plot2 = df_plot2.merge(events_df[['Century', 'Event', 'Event_ID']], on=['Century', 'Event'], how='left')
df_plot2 = df_plot2.sort_values('Century')

fig2 = px.line(df_plot2, x='Century', y='Population', title='Population of Rome per Century (Interpolated)', markers=True)

for _, row in df_plot2.dropna(subset=['Event_ID']).iterrows():
    fig2.add_annotation(
        x=row['Century'], 
        y=row['Population'],
        text=str(int(row['Event_ID'])),
        showarrow=True, arrowhead=2, ax=0, ay=-50,
        font=dict(size=14, color='black'),
        arrowcolor='gray', xanchor='center', yanchor='top'
    )

event_list = "<br>".join([f"• {int(eID)}: {event}" for eID, event in zip(events_df['Event_ID'], events_df['Event'])])
fig2.add_annotation(
    x=0.01, y=0.99, xref='paper', yref='paper',
    text=f"<b>Event Legend:</b><br>{event_list}",
    showarrow=False,
    font=dict(size=10, color='black'),
    align='left',
    bordercolor='black', borderwidth=1, bgcolor='white', opacity=0.9
)

fig2.update_layout(
    xaxis=dict(dtick=1, range=[-8, 22]),
    yaxis_title="Population",
    margin=dict(l=40, r=40, t=60, b=40)
)

# ------------------------------------------------------------------------
# Figure 3: Churches Dedicated to Mary per Century
# ------------------------------------------------------------------------
query_mary = """
    SELECT m.built_century, COUNT(*) AS count
    FROM RomanChurches_Main m
    JOIN RomanChurches_Details d ON m.cid = d.cid
    WHERE d.dedication LIKE '%Mary%' AND m.built_century <= 21
    GROUP BY m.built_century
"""
df_mary = pd.read_sql_query(text(query_mary), engine)

fig3 = px.bar(
    df_mary,
    x='built_century',
    y='count',
    title='Number of Churches Dedicated to the Virgin Mary per Century',
    text='count'
)
fig3.update_layout(xaxis_title="Century", yaxis_title="Count", xaxis=dict(dtick=1))

# ------------------------------------------------------------------------
# Streamlit Layout
# ------------------------------------------------------------------------
st.title("Roman Churches Insights")

centuries_df = pd.read_sql_query(
    text("SELECT DISTINCT built_century FROM RomanChurches_Main ORDER BY built_century"),
    engine
)

selected_century = st.selectbox(
    "Select a Century to view what churches were built at that time in Rome",
    centuries_df['built_century'],
    key="century_selectbox"
)

details_query = text("""
    SELECT m.englishname, m.address, d.architect, d.dedication, d.artists
    FROM RomanChurches_Main m
    JOIN RomanChurches_Details d ON m.cid = d.cid
    WHERE m.built_century = :selected_century
""")
df_details = pd.read_sql_query(details_query, engine, params={"selected_century": selected_century})

st.plotly_chart(fig1, use_container_width=True)
st.plotly_chart(fig2, use_container_width=True)
st.plotly_chart(fig3, use_container_width=True)

st.dataframe(df_details)
