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
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    .main-header {
        font-size: 2.5rem;
        color: #1E88E5;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.8rem;
        color: #424242;
        margin-bottom: 1rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 1rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .data-table {
        border-radius: 10px;
        overflow: hidden;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
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
    
    # Ensure 'InvoiceDate' is in datetime format with mixed format handling
    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"], format='mixed')
    return df

def get_column_names():
    """Get the column names from the database."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sales_data LIMIT 1")
        return [description[0] for description in cursor.description]

def add_record(data):
    """Add a new record to the database with validation."""
    try:
        # Validate required fields
        required_fields = ["Retailer", "RetailerID", "InvoiceDate", "Product"]
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return False, f"Missing required fields: {', '.join(missing_fields)}"

        with get_connection() as conn:
            cursor = conn.cursor()
            
            # Define the exact columns in the order they appear in the database
            columns = [
                "Retailer", "RetailerID", "InvoiceDate", "Region", "State", 
                "City", "Product", "PriceperUnit", "UnitsSold", "TotalSales", 
                "OperatingProfit", "OperatingMargin", "SalesMethod"
            ]
            
            # Filter out any extra fields not in our database
            available_fields = [field for field in columns if field in data]
            
            # Create the INSERT query
            placeholders = ", ".join(["?" for _ in available_fields])
            fields = ", ".join(available_fields)
            query = f"INSERT INTO sales_data ({fields}) VALUES ({placeholders})"
            
            # Convert values to SQLite-compatible formats
            values = []
            for field in available_fields:
                value = data[field]
                if isinstance(value, pd.Timestamp) or isinstance(value, datetime.datetime):
                    value = value.strftime('%Y-%m-%d %H:%M:%S')
                values.append(value)
            
            # Execute the insert
            cursor.execute(query, values)
            conn.commit()
            
            logger.info("Successfully added new record")
            return True, "Record added successfully!"
            
    except Exception as e:
        logger.error(f"Error adding record: {str(e)}")
        return False, f"Error adding record: {str(e)}"

def update_record(record_index, data):
    """Update an existing record with validation."""
    try:
        # Validate required fields
        required_fields = ["Retailer", "RetailerID", "InvoiceDate", "Product"]
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return False, f"Missing required fields: {', '.join(missing_fields)}"

        with get_connection() as conn:
            cursor = conn.cursor()
            
            # Define the exact columns in the order they appear in the database
            columns = [
                "Retailer", "RetailerID", "InvoiceDate", "Region", "State", 
                "City", "Product", "PriceperUnit", "UnitsSold", "TotalSales", 
                "OperatingProfit", "OperatingMargin", "SalesMethod"
            ]
            
            # Create SET clause for the update
            available_fields = [field for field in columns if field in data]
            set_clause = ", ".join([f"{field} = ?" for field in available_fields])
            
            # Convert values to SQLite-compatible formats
            values = []
            for field in available_fields:
                value = data[field]
                if isinstance(value, pd.Timestamp) or isinstance(value, datetime.datetime):
                    value = value.strftime('%Y-%m-%d %H:%M:%S')
                values.append(value)
            
            # Get the record we want to update
            df = fetch_data()
            if record_index >= len(df):
                return False, "Invalid record index"
            
            record = df.iloc[record_index]
            
            # Create WHERE clause using RetailerID, InvoiceDate, and Product for unique identification
            where_clause = "RetailerID = ? AND date(InvoiceDate) = date(?) AND Product = ?"
            where_values = [
                int(record["RetailerID"]),  # Ensure RetailerID is an integer
                record["InvoiceDate"].strftime('%Y-%m-%d'),  # Only compare the date part
                record["Product"]
            ]
            
            # Combine all values
            all_values = values + where_values
            
            query = f"UPDATE sales_data SET {set_clause} WHERE {where_clause}"
            
            # Log the query and values for debugging
            logger.info(f"Update query: {query}")
            logger.info(f"Update values: {all_values}")
            
            # First verify if the record exists
            verify_query = "SELECT COUNT(*) FROM sales_data WHERE RetailerID = ? AND date(InvoiceDate) = date(?) AND Product = ?"
            cursor.execute(verify_query, where_values)
            count = cursor.fetchone()[0]
            
            if count == 0:
                return False, "Record not found in database. It may have been deleted."
            
            # Execute the update
            cursor.execute(query, all_values)
            
            if cursor.rowcount == 0:
                return False, "No changes were made. The new values might be the same as the existing ones."
            
            conn.commit()
            logger.info(f"Successfully updated record at index {record_index}")
            return True, "Record updated successfully!"
            
    except Exception as e:
        logger.error(f"Error updating record: {str(e)}")
        return False, f"Error updating record: {str(e)}"

def delete_record(record_index):
    """Delete a record from the database."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            
            # Get the record we want to delete
            df = fetch_data()
            if record_index >= len(df):
                return False, "Invalid record index"
            
            record = df.iloc[record_index]
            
            # Create WHERE clause using RetailerID, InvoiceDate, and Product for unique identification
            where_clause = "RetailerID = ? AND date(InvoiceDate) = date(?) AND Product = ?"
            where_values = [
                int(record["RetailerID"]),  # Ensure RetailerID is an integer
                record["InvoiceDate"].strftime('%Y-%m-%d'),  # Only compare the date part
                record["Product"]
            ]
            
            # First verify if the record exists
            verify_query = "SELECT COUNT(*) FROM sales_data WHERE RetailerID = ? AND date(InvoiceDate) = date(?) AND Product = ?"
            cursor.execute(verify_query, where_values)
            count = cursor.fetchone()[0]
            
            if count == 0:
                return False, "Record not found in database. It may have been deleted."
            
            # Execute the delete
            query = f"DELETE FROM sales_data WHERE {where_clause}"
            cursor.execute(query, where_values)
            
            if cursor.rowcount == 0:
                return False, "No record was deleted. Please try again."
            
            conn.commit()
            logger.info(f"Successfully deleted record at index {record_index}")
            return True, "Record deleted successfully!"
            
    except Exception as e:
        logger.error(f"Error deleting record: {str(e)}")
        return False, f"Error deleting record: {str(e)}"

def signup():
    st.subheader("Signup")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    role = st.selectbox("Role", ["Admin", "User"])
    if st.button("Register"):
        users = load_users()
        if username in users:
            st.error("Username already exists. Choose a different one.")
        else:
            users[username] = {"password": password, "role": role}
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
    if st.session_state["page"] == "data_management":
        # Only Admin can access data management
        if st.session_state["role"] != "Admin":
            st.error("You don't have permission to access this page. Only Admin users can manage data.")
            return
        
        # Import and call the manage_data function from data_management.py
        import data_management
        data_management.manage_data()
        return

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
        st.markdown(f"<p>Welcome, {st.session_state['username']} ({st.session_state['role']})</p>", unsafe_allow_html=True)

    # Load Data from SQL
    df = fetch_data()
    
    # Sidebar: Navigation and Filters
    with st.sidebar:
        st.markdown("<h2>Navigation</h2>", unsafe_allow_html=True)
        if st.button("📊 Dashboard", use_container_width=True):
            st.session_state["page"] = "dashboard"
            st.rerun()
        if st.session_state["role"] == "Admin":
            if st.button("📝 Manage Data", use_container_width=True):
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