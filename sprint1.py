import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
from PIL import Image

# Set page configuration - MUST be the first Streamlit command
st.set_page_config(
    layout="wide",
    page_title="Sales Analytics Dashboard",
    page_icon="📊"
)

# Custom CSS
st.markdown("""
    <style>
    .stButton>button {
        border-radius: 5px;
        padding: 10px 20px;
        border: none;
        font-weight: bold;
    }
    .stTextInput>div>div>input {
        border-radius: 5px;
    }
    .stSelectbox>div>div>select {
        border-radius: 5px;
    }
    .stDateInput>div>div>input {
        border-radius: 5px;
    }
    .css-1d391kg {
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .css-1v0mbdj {
        border-radius: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

DB_PATH = "sales_data.db"  # SQLite Database Path

# Connect to SQL Database
def get_connection():
    return sqlite3.connect(DB_PATH)

# Fetch Data from SQL
def fetch_data():
    conn = get_connection()
    query = "SELECT * FROM sales_data"
    df = pd.read_sql(query, conn)
    conn.close()
    
    # Ensure 'InvoiceDate' is in datetime format
    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"])
    return df

def main():
    # Main Dashboard Layout
    st.markdown('<style>div.block-container{padding-top:1rem;}</style>', unsafe_allow_html=True)
    
    # Header with Logo and Title
    col1, col2 = st.columns([0.1, 0.9])
    with col1:
        try:
            image = Image.open('shoe.jpg')
            st.image(image, width=100)
        except FileNotFoundError:
            st.warning("⚠️ Logo not found. Ensure 'shoe.jpg' is in the app directory.")
    with col2:
        st.markdown("<h1>Interactive Sales Dashboard</h1>", unsafe_allow_html=True)

    # Load Data from SQL
    df = fetch_data()
    
    # Sidebar: Filters
    with st.sidebar:
        st.markdown("<h2>Filters</h2>", unsafe_allow_html=True)
        start_date = st.date_input("Start Date", df["InvoiceDate"].min())
        end_date = st.date_input("End Date", df["InvoiceDate"].max())

        st.markdown("<h2>Drill-down Reports</h2>", unsafe_allow_html=True)
        selected_retailer = st.selectbox("Select a Retailer", ["All"] + list(df["Retailer"].unique()))
        selected_state = st.selectbox("Select a State", ["All"] + list(df["State"].unique()))

    # Filter Data
    filtered_df = df[(df["InvoiceDate"] >= pd.to_datetime(start_date)) & (df["InvoiceDate"] <= pd.to_datetime(end_date))]
    if selected_retailer != "All":
        filtered_df = filtered_df[filtered_df["Retailer"] == selected_retailer]
    if selected_state != "All":
        filtered_df = filtered_df[filtered_df["State"] == selected_state]

    # Main Content
    st.markdown("<h2>Sales Overview</h2>", unsafe_allow_html=True)
    
    # Key Metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Sales", f"${filtered_df['TotalSales'].sum():,.2f}")
    with col2:
        st.metric("Units Sold", f"{filtered_df['UnitsSold'].sum():,}")
    with col3:
        st.metric("Average Sale", f"${filtered_df['TotalSales'].mean():,.2f}")
    with col4:
        st.metric("Number of Transactions", f"{len(filtered_df):,}")

    # Charts
    col1, col2 = st.columns(2)
    with col1:
        fig = px.bar(filtered_df, x="Retailer", y="TotalSales", title="Total Sales by Retailer")
        fig.update_layout(template='plotly')
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        filtered_df["Month_Year"] = filtered_df["InvoiceDate"].dt.to_period("M").astype(str)
        result = filtered_df.groupby("Month_Year")["TotalSales"].sum().reset_index()
        result["Month_Year"] = pd.to_datetime(result["Month_Year"])
        result = result.sort_values("Month_Year")
        result["Month_Year"] = result["Month_Year"].dt.strftime("%b'%y")
        
        fig1 = px.line(result, x="Month_Year", y="TotalSales", title="Total Sales Over Time")
        fig1.update_layout(template='plotly')
        st.plotly_chart(fig1, use_container_width=True)

    # Regional Analysis
    st.markdown("<h2>Regional Analysis</h2>", unsafe_allow_html=True)
    result1 = filtered_df.groupby("State")[["TotalSales", "UnitsSold"]].sum().reset_index()
    fig3 = go.Figure()
    fig3.add_trace(go.Bar(x=result1["State"], y=result1["TotalSales"], name="Total Sales"))
    fig3.add_trace(go.Scatter(x=result1["State"], y=result1["UnitsSold"], mode="lines", name="Units Sold", yaxis="y2"))
    fig3.update_layout(
        title="Total Sales and Units Sold by State",
        template='plotly',
        xaxis_title="State",
        yaxis_title="Total Sales",
        yaxis2=dict(title="Units Sold", overlaying="y", side="right")
    )
    st.plotly_chart(fig3, use_container_width=True)

    # Treemap
    st.markdown("<h2>Regional Sales Distribution</h2>", unsafe_allow_html=True)
    treemap = df[["Region", "City", "TotalSales"]].groupby(by=["Region", "City"])["TotalSales"].sum().reset_index()
    fig_treemap = px.treemap(
        treemap,
        path=["Region", "City"],
        values="TotalSales",
        title="Sales Distribution by Region and City",
        color="TotalSales",
        color_continuous_scale="blues"
    )
    fig_treemap.update_layout(template='plotly')
    st.plotly_chart(fig_treemap, use_container_width=True)

if __name__ == "__main__":
    main()