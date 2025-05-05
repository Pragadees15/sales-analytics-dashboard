import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
import logging
import time

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Custom CSS for better styling
st.markdown("""
<style>
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
    .stButton>button {
        background-color: #1E88E5;
        color: white;
        border-radius: 5px;
        padding: 0.5rem 1rem;
        font-weight: bold;
    }
    .stButton>button:hover {
        background-color: #1565C0;
    }
    .data-table {
        border-radius: 10px;
        overflow: hidden;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

def get_connection():
    """Create a connection to the SQLite database."""
    return sqlite3.connect("sales_data.db")

def fetch_data():
    """Fetch all data from the sales_data table."""
    with get_connection() as conn:
        query = "SELECT * FROM sales_data"
        df = pd.read_sql(query, conn)
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
                if isinstance(value, pd.Timestamp) or isinstance(value, datetime):
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
                if isinstance(value, pd.Timestamp) or isinstance(value, datetime):
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

def manage_data():
    """Main function to manage data in the Streamlit app."""
    # Add custom CSS
    st.markdown("""
        <style>
        .stApp {
            max-width: 100%;
            margin: 0 auto;
            background-color: #0E1117;
            color: white;
        }
        .header {
            padding: 1rem;
            background-color: #262730;
            border-radius: 0.5rem;
            margin-bottom: 2rem;
            color: white;
        }
        .metric-card {
            background-color: #262730;
            padding: 1rem;
            border-radius: 0.5rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
            margin-bottom: 1rem;
            color: white;
        }
        .metric-card h2, .metric-card h3 {
            color: white;
        }
        .back-button {
            background-color: #1E88E5;
            color: white;
            border-radius: 5px;
            padding: 0.5rem 1rem;
            font-weight: bold;
            margin-bottom: 1rem;
        }
        div[data-testid="stDataFrame"] {
            background-color: #262730;
        }
        div.stSelectbox > div > div > div {
            background-color: #262730;
            color: white;
        }
        div.stSelectbox > div > div {
            background-color: #262730;
            color: white;
        }
        .stDataFrame table {
            background-color: #262730;
            color: white;
        }
        .stDataFrame th {
            background-color: #1E1E1E;
            color: white;
        }
        .stDataFrame td {
            background-color: #262730;
            color: white;
        }
        div[data-testid="stForm"] {
            background-color: #262730;
            padding: 1rem;
            border-radius: 0.5rem;
            margin-bottom: 1rem;
        }
        </style>
    """, unsafe_allow_html=True)

    # Back button
    if st.button("⬅️ Back to Dashboard", key="back_to_dashboard"):
        st.session_state["page"] = "dashboard"
        st.rerun()

    # Header with dark theme
    st.markdown("""
        <div class="header">
            <h1 style="color: white;">Sales Data Management</h1>
        </div>
    """, unsafe_allow_html=True)

    # Sidebar filters
    st.sidebar.title("Filters")
    
    # Get data
    df = fetch_data()
    
    # Date range filter
    min_date = pd.to_datetime(df['InvoiceDate']).min()
    max_date = pd.to_datetime(df['InvoiceDate']).max()
    date_range = st.sidebar.date_input(
        "Date Range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )

    # Retailer filter
    retailers = sorted(df['Retailer'].unique())
    selected_retailers = st.sidebar.multiselect("Retailer", retailers)

    # Region filter
    regions = sorted(df['Region'].unique())
    selected_regions = st.sidebar.multiselect("Region", regions)

    # Product filter
    products = sorted(df['Product'].unique())
    selected_products = st.sidebar.multiselect("Product", products)

    # Apply filters
    filtered_df = df.copy()
    
    if len(date_range) == 2:
        filtered_df = filtered_df[
            (pd.to_datetime(filtered_df['InvoiceDate']).dt.date >= date_range[0]) &
            (pd.to_datetime(filtered_df['InvoiceDate']).dt.date <= date_range[1])
        ]
    
    if selected_retailers:
        filtered_df = filtered_df[filtered_df['Retailer'].isin(selected_retailers)]
    
    if selected_regions:
        filtered_df = filtered_df[filtered_df['Region'].isin(selected_regions)]
    
    if selected_products:
        filtered_df = filtered_df[filtered_df['Product'].isin(selected_products)]

    # Display metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("""
            <div class="metric-card">
                <h3>Total Records</h3>
                <h2>{:,}</h2>
            </div>
        """.format(len(filtered_df)), unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
            <div class="metric-card">
                <h3>Total Sales</h3>
                <h2>${:,.2f}</h2>
            </div>
        """.format(filtered_df['TotalSales'].sum()), unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
            <div class="metric-card">
                <h3>Units Sold</h3>
                <h2>{:,}</h2>
            </div>
        """.format(filtered_df['UnitsSold'].sum()), unsafe_allow_html=True)
    
    with col4:
        st.markdown("""
            <div class="metric-card">
                <h3>Operating Profit</h3>
                <h2>${:,.2f}</h2>
            </div>
        """.format(filtered_df['OperatingProfit'].sum()), unsafe_allow_html=True)

    # Data visualization options
    st.subheader("Data Visualization")
    viz_option = st.selectbox(
        "Choose visualization",
        ["Sales Trend", "Regional Distribution", "Product Performance"]
    )

    if viz_option == "Sales Trend":
        daily_sales = filtered_df.groupby(pd.to_datetime(filtered_df['InvoiceDate']).dt.date)['TotalSales'].sum().reset_index()
        fig = px.line(daily_sales, x='InvoiceDate', y='TotalSales', title='Daily Sales Trend')
        st.plotly_chart(fig, use_container_width=True)
    
    elif viz_option == "Regional Distribution":
        regional_sales = filtered_df.groupby('Region')['TotalSales'].sum().reset_index()
        fig = px.pie(regional_sales, values='TotalSales', names='Region', title='Sales by Region')
        st.plotly_chart(fig, use_container_width=True)
    
    else:  # Product Performance
        product_performance = filtered_df.groupby('Product').agg({
            'TotalSales': 'sum',
            'UnitsSold': 'sum',
            'OperatingProfit': 'sum'
        }).reset_index()
        fig = px.bar(product_performance, x='Product', y='TotalSales', title='Product Sales Performance')
        st.plotly_chart(fig, use_container_width=True)

    # Show editable data table
    edited_df = st.data_editor(
        filtered_df,
        hide_index=True,
        use_container_width=True,
        num_rows="dynamic",
        key="editable_data"
    )

    # Save changes button
    if st.button("Save Changes"):
        changes = edited_df.compare(filtered_df)
        if not changes.empty:
            for idx in changes.index:
                row_data = edited_df.loc[idx].to_dict()
                success, message = update_record(idx, row_data)
                if success:
                    st.success(f"Record at index {idx} updated.")
                else:
                    st.error(message)
            st.rerun()
        else:
            st.info("No changes detected.")

    # Add new record button
    if st.button("Add New Record"):
        st.session_state.adding_record = True

    if st.session_state.get('adding_record', False):
        with st.form("new_record_form"):
            st.write("Add New Record")
            new_data = {}
            columns = get_column_names()
            for col in columns:
                if col in ['TotalSales', 'OperatingProfit', 'OperatingMargin']:
                    continue  # Skip calculated fields
                if col == 'InvoiceDate':
                    new_data[col] = st.date_input(col)
                elif col in ['PriceperUnit', 'UnitsSold']:
                    new_data[col] = st.number_input(col, min_value=0.0, format='%f')
                else:
                    new_data[col] = st.text_input(col, value="")
            submitted = st.form_submit_button("Submit")
            if submitted:
                success, message = add_record(new_data)
                if success:
                    st.success(message)
                    st.session_state.adding_record = False
                    st.rerun()
                else:
                    st.error(message)

    # Row deletion (selectbox-based)
    filtered_df = filtered_df.reset_index(drop=True)
    if not filtered_df.empty:
        selected_index = st.selectbox(
            "Select a record to delete",
            filtered_df.index,
            format_func=lambda i: f"{filtered_df.loc[i, 'Retailer']} | {filtered_df.loc[i, 'InvoiceDate']} | {filtered_df.loc[i, 'Product']}"
        )
        if st.button("Delete Selected Record"):
            success, message = delete_record(selected_index)
            if success:
                st.success(message)
                st.rerun()
            else:
                st.error(message)
    else:
        st.info("No records available to delete.")

if __name__ == "__main__":
    manage_data()
