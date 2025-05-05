import streamlit as st
import pandas as pd
import datetime
import json
import sqlite3
from PIL import Image
import plotly.express as px
import plotly.graph_objects as go
from prophet import Prophet
import os
import secrets
import time

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

USER_DB = "users.json"
DB_PATH = "sales_data.db"

# Load Users from JSON File
def load_users():
    if os.path.exists(USER_DB):
        with open(USER_DB, "r") as file:
            return json.load(file)
    return {}

def save_users(users):
    with open(USER_DB, "w") as file:
        json.dump(users, file, indent=4)

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

def signup():
    st.subheader("Signup")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    user_type = st.selectbox("Select user type", ["User", "Admin"])
    if st.button("Register"):
        users = load_users()
        if username in users:
            st.error("Username already exists. Choose a different one.")
        else:
            users[username] = {"password": password, "role": user_type}
            save_users(users)
            st.success("Signup successful! Please log in.")

def generate_reset_token():
    return secrets.token_urlsafe(32)

def save_reset_token(username, token, expiry_minutes=15):
    users = load_users()
    if username in users:
        users[username]["reset_token"] = token
        users[username]["reset_token_expiry"] = time.time() + (expiry_minutes * 60)
        save_users(users)
        return True
    return False

def verify_reset_token(username, token):
    users = load_users()
    if username in users and "reset_token" in users[username]:
        if (users[username]["reset_token"] == token and 
            time.time() < users[username]["reset_token_expiry"]):
            return True
    return False

def reset_password(username, token, new_password):
    users = load_users()
    if verify_reset_token(username, token):
        users[username]["password"] = new_password
        # Remove the reset token after successful password reset
        del users[username]["reset_token"]
        del users[username]["reset_token_expiry"]
        save_users(users)
        return True
    return False

def forgot_password():
    st.subheader("Forgot Password")
    username = st.text_input("Enter your username")
    if st.button("Reset Password"):
        users = load_users()
        if username in users:
            st.session_state["reset_username"] = username
            st.session_state["show_forgot_password"] = False
            st.session_state["show_reset_form"] = True
            st.rerun()
        else:
            st.error("Username not found. Please check your username and try again.")

def reset_password_form():
    st.subheader("Reset Password")
    new_password = st.text_input("New Password", type="password")
    confirm_password = st.text_input("Confirm Password", type="password")
    
    if st.button("Reset Password"):
        if new_password != confirm_password:
            st.error("Passwords do not match!")
            return
        
        users = load_users()
        if st.session_state["reset_username"] in users:
            users[st.session_state["reset_username"]]["password"] = new_password
            save_users(users)
            st.success("Password has been reset successfully! Please login with your new password.")
            # Clear reset session state
            del st.session_state["reset_username"]
            del st.session_state["show_reset_form"]
            st.rerun()
        else:
            st.error("Something went wrong. Please try again.")
    
    if st.button("Back to Login"):
        st.session_state["show_reset_form"] = False
        st.rerun()

def login():
    st.subheader("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        if st.button("Login"):
            users = load_users()
            if username in users and users[username]["password"] == password:
                st.session_state["logged_in"] = True
                st.session_state["username"] = username
                st.session_state["role"] = users[username]["role"]
                st.rerun()
            else:
                st.error("Invalid credentials")
    with col2:
        if st.button("Forgot Password?"):
            st.session_state["show_forgot_password"] = True
            st.rerun()

def main():
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False
    if "page" not in st.session_state:
        st.session_state["page"] = "dashboard"
    if "show_forgot_password" not in st.session_state:
        st.session_state["show_forgot_password"] = False
    if "show_reset_form" not in st.session_state:
        st.session_state["show_reset_form"] = False

    if not st.session_state["logged_in"]:
        st.markdown("<h1 style='text-align: center;'>Welcome to Sales Analytics</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center;'>Please login or signup to continue</p>", unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            if st.session_state["show_reset_form"]:
                reset_password_form()
            elif st.session_state["show_forgot_password"]:
                forgot_password()
                if st.button("Back to Login"):
                    st.session_state["show_forgot_password"] = False
                    st.rerun()
            else:
                option = st.radio("Select an option", ["Login", "Signup"], label_visibility="collapsed", horizontal=True)
                if option == "Login":
                    login()
                else:
                    signup()
        return

    # Handle navigation
    if st.session_state["page"] == "reports":
        import report_generation
        report_generation.main()
        return
    elif st.session_state["page"] == "data_management":
        import data_management
        data_management.manage_data()
        return

    # Main Dashboard Layout
    st.markdown('<style>div.block-container{padding-top:1rem;}</style>', unsafe_allow_html=True)
    
    # Header with Logo and Title
    col1, col2 = st.columns([0.1, 0.9])
    with col1:
        image = Image.open('shoe.jpg')
        st.image(image, width=100)
    with col2:
        st.markdown("<h1>Interactive Sales Dashboard</h1>", unsafe_allow_html=True)
        st.markdown(f"<p>Welcome, {st.session_state['username']} ({st.session_state['role']})</p>", unsafe_allow_html=True)

    # Load Data from SQL
    df = fetch_data()
    
    # Sidebar: Navigation and Filters
    with st.sidebar:
        st.markdown("<h2>Navigation</h2>", unsafe_allow_html=True)
        if st.button("📊 Dashboard", use_container_width=True):
            st.session_state["page"] = "dashboard"
            st.rerun()
        if st.button("📈 Generate Reports", use_container_width=True):
            st.session_state["page"] = "reports"
            st.rerun()
        if st.button("🗃️ Manage Data", use_container_width=True):
            st.session_state["page"] = "data_management"
            st.rerun()

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

    # Admin Features
    if st.session_state["role"] == "Admin":
        st.markdown("<h2>Advanced Analytics</h2>", unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            profit_data = filtered_df.groupby("Retailer")["OperatingProfit"].sum().reset_index()
            fig6 = px.bar(profit_data, x="Retailer", y="OperatingProfit", title="Operating Profit by Retailer")
            fig6.update_layout(template='plotly')
            st.plotly_chart(fig6, use_container_width=True)

        with col2:
            df_prophet = filtered_df.groupby("InvoiceDate")["TotalSales"].sum().reset_index()
            df_prophet.columns = ["ds", "y"]
            model = Prophet()
            model.fit(df_prophet)
            future = model.make_future_dataframe(periods=90)
            forecast = model.predict(future)
            fig5 = px.line(forecast, x="ds", y="yhat", title="Sales Forecast for Next 3 Months")
            fig5.update_layout(template='plotly')
            st.plotly_chart(fig5, use_container_width=True)

    # Logout Button
    if st.button("Logout", use_container_width=True):
        st.session_state.clear()
        st.rerun()

if __name__ == "__main__":
    main()
