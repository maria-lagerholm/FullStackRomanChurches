import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine, text
#https://github.com/ericleasemorgan/churches-of-rome/blob/master/etc/roman-churches.csv
# --- Database Connection ---
server = "OMEN"
engine_new = create_engine(f"mssql+pyodbc://@{server}/RomanChurches?driver=ODBC+Driver+17+for+SQL+Server")

# --- Figure 1: Number of Churches per Century ---
query_count = "SELECT built_century, COUNT(*) AS count FROM RomanChurches_Main GROUP BY built_century"
df_count = pd.read_sql_query(text(query_count), engine_new)
all_centuries = list(range(1, 22))
df_plot1 = pd.DataFrame({'built_century': all_centuries}).merge(df_count, on='built_century', how='left').fillna(0)
fig1 = px.bar(df_plot1, x='built_century', y='count', title='Number of churches built in Rome per century', text='count')
fig1.update_layout(xaxis_title="Century")
fig1.update_layout(yaxis_title="Count")
fig1.update_traces(texttemplate='%{text}', textposition='outside')
fig1.update_layout(xaxis=dict(dtick=1))

# --- Figure 2: Population of Rome (Interpolated) ---
df_pop = pd.read_sql("SELECT Century, Event, Population FROM RomanPopulation", engine_new)
df_pop['Century'] = df_pop['Century'].astype(int)
df_pop = df_pop[df_pop['Century'] <= 21]

centuries_full = list(range(-8, 22))
df_full = pd.DataFrame({'Century': centuries_full})
df_merged = df_full.merge(df_pop[['Century','Population']], on='Century', how='left')
df_merged['Population'] = df_merged['Population'].interpolate(method='linear')

df_events = df_pop[['Century','Event']].dropna()
df_plot2 = df_merged.merge(df_events, on='Century', how='left').fillna({'Event':''}).sort_values('Century')
events_df = df_plot2[df_plot2['Event']!=''].copy()
events_df['Event_ID'] = range(1, len(events_df)+1)
df_plot2 = df_plot2.merge(events_df[['Century','Event','Event_ID']], on=['Century','Event'], how='left')

fig2 = px.line(df_plot2, x='Century', y='Population', 
               title='Population of Rome per century (interpolated) https://en.wikipedia.org/wiki/Rome',
               markers=True, line_shape='spline')
for _, row in df_plot2.dropna(subset=['Event_ID']).iterrows():
    fig2.add_annotation(x=row['Century'], y=row['Population'], text=str(int(row['Event_ID'])),
                        showarrow=True, arrowhead=2, ax=0, ay=-50, font=dict(size=14, color='black'),
                        arrowcolor='gray', xanchor='center', yanchor='top')

event_list = "<br>".join([f"• {int(eID)}: {event}" for eID, event in zip(events_df['Event_ID'], events_df['Event'])])
max_pop = df_plot2['Population'].max()
fig2.add_annotation(x=0.01, y=0.99, xref='paper', yref='paper', 
                    text="<b>Event Legend:</b><br>"+event_list,
                    showarrow=False, font=dict(size=10, color='black'),
                    align='left', bordercolor='black', borderwidth=1, bgcolor='white', opacity=0.9)
fig2.update_layout(xaxis=dict(dtick=1, range=[-8,22]),
                   yaxis=dict(dtick=500000, range=[0, max_pop*1.3]))

# --- Figure 3: Churches Dedicated to Mary ---
query_mary = """
    SELECT m.built_century, COUNT(*) AS count
    FROM RomanChurches_Main m
    JOIN RomanChurches_Details d ON m.cid = d.cid
    WHERE d.dedication LIKE '%Mary%' AND m.built_century <= 21
    GROUP BY m.built_century
    ORDER BY m.built_century
"""
df_mary = pd.read_sql_query(text(query_mary), engine_new)
fig3 = px.bar(df_mary, x='built_century', y='count', 
              title='Number of churches dedicated to Virgin Mary per century', text='count')
fig3.update_layout(xaxis_title="Century")
fig3.update_layout(yaxis_title="Count")
fig3.update_traces(texttemplate='%{text}', textposition='outside')
fig3.update_layout(xaxis=dict(dtick=1))

# --- Streamlit Display ---
st.title("Roman Churches Insights")
st.plotly_chart(fig1)
st.plotly_chart(fig2)
st.plotly_chart(fig3)

# --- Century Selection & Details ---
centuries_df = pd.read_sql_query(text("SELECT DISTINCT built_century FROM RomanChurches_Main ORDER BY built_century"), engine_new)
selected_century = st.selectbox("Select a Century", centuries_df['built_century'])
details_query = text("""
    SELECT m.englishname, m.address, d.architect, d.dedication, d.artists
    FROM RomanChurches_Main m
    JOIN RomanChurches_Details d ON m.cid = d.cid
    WHERE m.built_century = :selected_century
""")
df_details = pd.read_sql_query(details_query, engine_new, params={"selected_century": selected_century})
st.dataframe(df_details)
