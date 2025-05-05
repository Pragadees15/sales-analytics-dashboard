import streamlit as st
import pandas as pd
from datetime import datetime
import sqlite3
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
from io import BytesIO
import pydeck as pdk

def get_connection():
    return sqlite3.connect("sales_data.db")

def fetch_data():
    conn = get_connection()
    query = "SELECT * FROM sales_data"
    df = pd.read_sql(query, conn)
    conn.close()
    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"])
    return df

def calculate_metrics(data):
    metrics = {
        "total_sales": data["TotalSales"].sum(),
        "total_units": data["UnitsSold"].sum(),
        "avg_sale": data["TotalSales"].mean(),
        "profit_margin": (data["OperatingProfit"].sum() / data["TotalSales"].sum()) * 100,
        "top_retailer": data.groupby("Retailer")["TotalSales"].sum().idxmax(),
        "top_product": data.groupby("Product")["TotalSales"].sum().idxmax(),
        "top_state": data.groupby("State")["TotalSales"].sum().idxmax()
    }
    return metrics

def generate_excel_report(data, report_type, date_range=None):
    # Create progress bar
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    progress_bar.progress(20)
    status_text.text("Preparing data...")
    
    # Create Excel writer
    filename = f"Sales_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    writer = pd.ExcelWriter(filename, engine='xlsxwriter')
    
    # 1. Summary Metrics
    progress_bar.progress(30)
    status_text.text("Creating summary metrics...")
    
    metrics = calculate_metrics(data)
    summary_data = {
        'Metric': [
            'Total Sales',
            'Total Units Sold',
            'Average Sale',
            'Profit Margin',
            'Top Retailer',
            'Top Product',
            'Top State'
        ],
        'Value': [
            f"${metrics['total_sales']:,.2f}",
            f"{metrics['total_units']:,}",
            f"${metrics['avg_sale']:,.2f}",
            f"{metrics['profit_margin']:.2f}%",
            metrics['top_retailer'],
            metrics['top_product'],
            metrics['top_state']
        ]
    }
    pd.DataFrame(summary_data).to_excel(writer, sheet_name='Summary', index=False)
    
    # 2. Sales Trend
    progress_bar.progress(40)
    status_text.text("Analyzing sales trends...")
    
    daily_sales = data.groupby('InvoiceDate').agg({
        'TotalSales': 'sum',
        'UnitsSold': 'sum',
        'OperatingProfit': 'sum'
    }).reset_index()
    daily_sales.to_excel(writer, sheet_name='Daily Sales', index=False)
    
    # 3. Product Performance
    progress_bar.progress(50)
    status_text.text("Analyzing product performance...")
    
    product_performance = data.groupby('Product').agg({
        'TotalSales': 'sum',
        'UnitsSold': 'sum',
        'OperatingProfit': 'sum'
    }).reset_index()
    product_performance['Profit Margin'] = (product_performance['OperatingProfit'] / product_performance['TotalSales'] * 100)
    product_performance = product_performance.sort_values('TotalSales', ascending=False)
    product_performance.to_excel(writer, sheet_name='Product Performance', index=False)
    
    # 4. Regional Analysis
    progress_bar.progress(60)
    status_text.text("Analyzing regional performance...")
    
    regional_performance = data.groupby(['Region', 'State']).agg({
        'TotalSales': 'sum',
        'UnitsSold': 'sum',
        'OperatingProfit': 'sum'
    }).reset_index()
    regional_performance['Profit Margin'] = (regional_performance['OperatingProfit'] / regional_performance['TotalSales'] * 100)
    regional_performance = regional_performance.sort_values('TotalSales', ascending=False)
    regional_performance.to_excel(writer, sheet_name='Regional Analysis', index=False)
    
    # 5. Retailer Analysis
    progress_bar.progress(70)
    status_text.text("Analyzing retailer performance...")
    
    retailer_performance = data.groupby('Retailer').agg({
        'TotalSales': 'sum',
        'UnitsSold': 'sum',
        'OperatingProfit': 'sum'
    }).reset_index()
    retailer_performance['Profit Margin'] = (retailer_performance['OperatingProfit'] / retailer_performance['TotalSales'] * 100)
    retailer_performance = retailer_performance.sort_values('TotalSales', ascending=False)
    retailer_performance.to_excel(writer, sheet_name='Retailer Performance', index=False)
    
    # 6. Monthly Trends
    progress_bar.progress(80)
    status_text.text("Analyzing monthly trends...")
    
    data['Month'] = data['InvoiceDate'].dt.to_period('M')
    monthly_trends = data.groupby('Month').agg({
        'TotalSales': 'sum',
        'UnitsSold': 'sum',
        'OperatingProfit': 'sum'
    }).reset_index()
    monthly_trends['Month'] = monthly_trends['Month'].astype(str)
    monthly_trends['Growth Rate'] = monthly_trends['TotalSales'].pct_change() * 100
    monthly_trends.to_excel(writer, sheet_name='Monthly Trends', index=False)
    
    # Format the Excel file
    progress_bar.progress(90)
    status_text.text("Formatting Excel file...")
    
    workbook = writer.book
    
    # Add formats
    header_format = workbook.add_format({
        'bold': True,
        'bg_color': '#D3D3D3',
        'border': 1
    })
    
    number_format = workbook.add_format({
        'num_format': '#,##0.00',
        'border': 1
    })
    
    percent_format = workbook.add_format({
        'num_format': '0.00%',
        'border': 1
    })
    
    # Apply formats to each sheet
    for sheet_name in writer.sheets:
        worksheet = writer.sheets[sheet_name]
        worksheet.set_column('A:Z', 15)  # Set column width
        
        # Get the dataframe for this sheet
        if sheet_name == 'Summary':
            df = pd.DataFrame(summary_data)
        elif sheet_name == 'Daily Sales':
            df = daily_sales
        elif sheet_name == 'Product Performance':
            df = product_performance
        elif sheet_name == 'Regional Analysis':
            df = regional_performance
        elif sheet_name == 'Retailer Performance':
            df = retailer_performance
        elif sheet_name == 'Monthly Trends':
            df = monthly_trends
        
        # Format headers
        for col_num, value in enumerate(df.columns):
            worksheet.write(0, col_num, value, header_format)
        
        # Format numbers and handle NaN values
        for row in range(1, len(df) + 1):
            for col in range(len(df.columns)):
                cell_value = df.iloc[row-1, col]
                if pd.isna(cell_value) or cell_value is None:  # Handle NaN and None values
                    worksheet.write_blank(row, col, None)
                elif isinstance(cell_value, (int, float)):
                    if 'Margin' in df.columns[col] or 'Rate' in df.columns[col]:
                        worksheet.write_number(row, col, cell_value, percent_format)
                    else:
                        worksheet.write_number(row, col, cell_value, number_format)
                else:
                    worksheet.write(row, col, str(cell_value))
    
    # Save the Excel file
    writer.close()
    
    progress_bar.progress(100)
    status_text.text("Report generation complete!")
    
    return filename

def main():
    st.markdown("<h1 class='main-header'>Report Generation</h1>", unsafe_allow_html=True)
    
    # Navigation
    with st.sidebar:
        st.markdown("### Navigation")
        if st.button("⬅️ Back to Dashboard", use_container_width=True):
            st.session_state["page"] = "dashboard"
            st.rerun()
        
        st.markdown("### Report Options")
        report_type = st.selectbox(
            "Select Report Type",
            ["Sales Summary", "Product Performance", "Regional Analysis"]
        )
        
        # Date range selector
        df = fetch_data()
        min_date = df["InvoiceDate"].min()
        max_date = df["InvoiceDate"].max()
        date_range = st.date_input(
            "Select Date Range",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date
        )
        
        # Retailer filter
        retailers = ["All"] + sorted(df["Retailer"].unique().tolist())
        selected_retailer = st.selectbox("Filter by Retailer", retailers)
        
        # Region filter
        regions = ["All"] + sorted(df["Region"].unique().tolist())
        selected_region = st.selectbox("Filter by Region", regions)
        
        # Product filter
        products = ["All"] + sorted(df["Product"].unique().tolist())
        selected_product = st.selectbox("Filter by Product", products)
    
    # Apply filters
    filtered_df = df[
        (df["InvoiceDate"].dt.date >= date_range[0]) &
        (df["InvoiceDate"].dt.date <= date_range[1])
    ]
    
    if selected_retailer != "All":
        filtered_df = filtered_df[filtered_df["Retailer"] == selected_retailer]
    if selected_region != "All":
        filtered_df = filtered_df[filtered_df["Region"] == selected_region]
    if selected_product != "All":
        filtered_df = filtered_df[filtered_df["Product"] == selected_product]
    
    # Generate report based on type
    if report_type == "Sales Summary":
        generate_sales_summary(filtered_df)
    elif report_type == "Product Performance":
        generate_product_performance(filtered_df)
    else:  # Regional Analysis
        generate_regional_analysis(filtered_df)
    
    # Export options
    st.markdown("### Export Report")
    export_format = st.selectbox("Select Export Format", ["Excel", "CSV"])
    
    if st.button("Export Report"):
        if export_format == "Excel":
            export_to_excel(filtered_df, report_type)
            st.success("Report exported to Excel successfully!")
        else:
            export_to_csv(filtered_df, report_type)
            st.success("Report exported to CSV successfully!")

def generate_sales_summary(df):
    st.markdown("## Sales Summary Report")
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Sales", f"${df['TotalSales'].sum():,.2f}")
    with col2:
        st.metric("Total Units", f"{df['UnitsSold'].sum():,}")
    with col3:
        st.metric("Avg. Order Value", f"${df['TotalSales'].mean():,.2f}")
    with col4:
        st.metric("Operating Profit", f"${df['OperatingProfit'].sum():,.2f}")
    
    # Sales trend
    st.markdown("### Sales Trend")
    sales_trend = df.groupby("InvoiceDate")["TotalSales"].sum().reset_index()
    fig = px.line(sales_trend, x="InvoiceDate", y="TotalSales", title="Daily Sales Trend")
    fig.update_layout(template='plotly_white')
    st.plotly_chart(fig, use_container_width=True)
    
    # Top retailers
    st.markdown("### Top Retailers")
    top_retailers = df.groupby("Retailer").agg({
        "TotalSales": "sum",
        "UnitsSold": "sum",
        "OperatingProfit": "sum"
    }).reset_index().sort_values("TotalSales", ascending=False).head(10)
    
    fig = px.bar(top_retailers, x="Retailer", y="TotalSales",
                 title="Top 10 Retailers by Sales")
    fig.update_layout(template='plotly_white')
    st.plotly_chart(fig, use_container_width=True)
    
    # Sales method distribution
    st.markdown("### Sales Method Distribution")
    sales_method = df.groupby("SalesMethod")["TotalSales"].sum().reset_index()
    fig = px.pie(sales_method, values="TotalSales", names="SalesMethod",
                 title="Sales Distribution by Method")
    fig.update_layout(template='plotly_white')
    st.plotly_chart(fig, use_container_width=True)

def generate_product_performance(df):
    st.markdown("## Product Performance Report")
    
    # Product metrics
    product_metrics = df.groupby("Product").agg({
        "TotalSales": "sum",
        "UnitsSold": "sum",
        "OperatingProfit": "sum",
        "OperatingMargin": "mean"
    }).reset_index()
    
    # Top products by sales
    st.markdown("### Top Products by Sales")
    top_products = product_metrics.sort_values("TotalSales", ascending=False).head(10)
    fig = px.bar(top_products, x="Product", y="TotalSales",
                 title="Top 10 Products by Sales")
    fig.update_layout(template='plotly_white')
    st.plotly_chart(fig, use_container_width=True)
    
    # Product profitability
    st.markdown("### Product Profitability")
    fig = px.scatter(product_metrics, x="TotalSales", y="OperatingMargin",
                    size="UnitsSold", color="Product",
                    title="Product Profitability Analysis")
    fig.update_layout(template='plotly_white')
    st.plotly_chart(fig, use_container_width=True)
    
    # Units sold by product
    st.markdown("### Units Sold by Product")
    fig = px.bar(product_metrics.sort_values("UnitsSold", ascending=False),
                 x="Product", y="UnitsSold", title="Units Sold by Product")
    fig.update_layout(template='plotly_white')
    st.plotly_chart(fig, use_container_width=True)

def generate_regional_analysis(df):
    st.markdown("## Regional Analysis Report")
    
    # Regional metrics
    regional_metrics = df.groupby(["Region", "State"]).agg({
        "TotalSales": "sum",
        "UnitsSold": "sum",
        "OperatingProfit": "sum"
    }).reset_index()
    
    # Sales by region
    st.markdown("### Sales by Region")
    region_sales = regional_metrics.groupby("Region")["TotalSales"].sum().reset_index()
    fig = px.pie(region_sales, values="TotalSales", names="Region",
                 title="Sales Distribution by Region")
    fig.update_layout(template='plotly_white')
    st.plotly_chart(fig, use_container_width=True)
    
    # State performance using scatterplot map
    st.markdown("### State Performance")
    
    # Prepare data for scatterplot map
    state_data = regional_metrics.groupby("State").agg({
        "TotalSales": "sum",
        "UnitsSold": "sum",
        "OperatingProfit": "sum"
    }).reset_index()
    
    # Create a dictionary to map state names to their abbreviations
    state_abbrev = {
        'Alabama': 'AL', 'Alaska': 'AK', 'Arizona': 'AZ', 'Arkansas': 'AR', 'California': 'CA',
        'Colorado': 'CO', 'Connecticut': 'CT', 'Delaware': 'DE', 'Florida': 'FL', 'Georgia': 'GA',
        'Hawaii': 'HI', 'Idaho': 'ID', 'Illinois': 'IL', 'Indiana': 'IN', 'Iowa': 'IA',
        'Kansas': 'KS', 'Kentucky': 'KY', 'Louisiana': 'LA', 'Maine': 'ME', 'Maryland': 'MD',
        'Massachusetts': 'MA', 'Michigan': 'MI', 'Minnesota': 'MN', 'Mississippi': 'MS', 'Missouri': 'MO',
        'Montana': 'MT', 'Nebraska': 'NE', 'Nevada': 'NV', 'New Hampshire': 'NH', 'New Jersey': 'NJ',
        'New Mexico': 'NM', 'New York': 'NY', 'North Carolina': 'NC', 'North Dakota': 'ND', 'Ohio': 'OH',
        'Oklahoma': 'OK', 'Oregon': 'OR', 'Pennsylvania': 'PA', 'Rhode Island': 'RI', 'South Carolina': 'SC',
        'South Dakota': 'SD', 'Tennessee': 'TN', 'Texas': 'TX', 'Utah': 'UT', 'Vermont': 'VT',
        'Virginia': 'VA', 'Washington': 'WA', 'West Virginia': 'WV', 'Wisconsin': 'WI', 'Wyoming': 'WY'
    }
    
    # Add state abbreviation column
    state_data['state_code'] = state_data['State'].map(state_abbrev)
    
    # Add state coordinates
    state_coords = {
        'AL': [32.7794, -86.8287], 'AK': [61.2167, -149.9000], 'AZ': [34.2744, -111.6602], 
        'AR': [34.8938, -92.4426], 'CA': [37.1841, -119.4696], 'CO': [38.9972, -105.5478], 
        'CT': [41.6219, -72.7273], 'DE': [39.1451, -75.4189], 'FL': [28.6305, -82.4497], 
        'GA': [32.6415, -83.4426], 'HI': [20.2927, -156.3737], 'ID': [45.3505, -114.6130], 
        'IL': [40.0417, -89.1965], 'IN': [39.8942, -86.2816], 'IA': [42.0751, -93.4960], 
        'KS': [38.5266, -96.7265], 'KY': [37.5347, -85.3021], 'LA': [31.1694, -91.8678], 
        'ME': [45.3695, -69.2428], 'MD': [39.0550, -76.7909], 'MA': [42.2596, -71.8083], 
        'MI': [43.3266, -84.5361], 'MN': [45.6945, -93.9002], 'MS': [32.7416, -89.6787], 
        'MO': [38.3566, -92.4580], 'MT': [47.0527, -109.6333], 'NE': [41.1254, -98.2683], 
        'NV': [39.3289, -116.6312], 'NH': [43.4526, -71.5639], 'NJ': [40.2989, -74.5210], 
        'NM': [34.8405, -106.2485], 'NY': [42.1658, -74.9481], 'NC': [35.5557, -79.3877], 
        'ND': [47.4501, -100.4659], 'OH': [40.2862, -82.7937], 'OK': [35.5376, -96.9247], 
        'OR': [44.1419, -120.5381], 'PA': [40.5906, -77.2098], 'RI': [41.6762, -71.5562], 
        'SC': [33.9169, -80.8964], 'SD': [44.2998, -99.4388], 'TN': [35.8580, -86.3505], 
        'TX': [31.1694, -100.0000], 'UT': [40.1135, -111.8535], 'VT': [44.0687, -72.6658], 
        'VA': [37.5215, -78.8537], 'WA': [47.3826, -120.4472], 'WV': [38.6409, -80.6227], 
        'WI': [44.6243, -89.9941], 'WY': [42.9957, -107.5512]
    }
    
    # Add coordinates to the dataframe
    state_data['lat'] = state_data['state_code'].map(lambda x: state_coords.get(x, [0, 0])[0])
    state_data['lon'] = state_data['state_code'].map(lambda x: state_coords.get(x, [0, 0])[1])
    
    # Create scatterplot map
    fig = px.scatter_mapbox(
        state_data,
        lat="lat",
        lon="lon",
        hover_name="State",
        hover_data={
            "TotalSales": ":$,.2f",
            "UnitsSold": ":,",
            "OperatingProfit": ":$,.2f",
            "lat": False,
            "lon": False
        },
        color="TotalSales",
        size="UnitsSold",
        color_continuous_scale="Viridis",
        size_max=50,
        zoom=3,
        title="Sales Distribution by State",
        mapbox_style="carto-positron"
    )
    
    fig.update_layout(
        margin={"r":0, "t":30, "l":0, "b":0},
        height=600
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Add a bar chart for state performance
    st.markdown("### State Performance (Bar Chart)")
    fig_bar = px.bar(
        state_data.sort_values("TotalSales", ascending=False).head(15),
        x="State",
        y="TotalSales",
        color="OperatingProfit",
        title="Top 15 States by Sales",
        labels={"TotalSales": "Total Sales ($)", "OperatingProfit": "Operating Profit ($)"}
    )
    fig_bar.update_layout(template='plotly_white')
    st.plotly_chart(fig_bar, use_container_width=True)
    
    # Top cities
    st.markdown("### Top Cities")
    city_metrics = df.groupby("City")["TotalSales"].sum().reset_index()
    top_cities = city_metrics.sort_values("TotalSales", ascending=False).head(10)
    fig = px.bar(top_cities, x="City", y="TotalSales",
                 title="Top 10 Cities by Sales")
    fig.update_layout(template='plotly_white')
    st.plotly_chart(fig, use_container_width=True)

def export_to_excel(df, report_type):
    """Export the filtered data to Excel with formatting and multiple sheets for each visualization."""
    try:
        # Create a BytesIO object to store the Excel file
        output = BytesIO()
        
        # Create Excel writer object
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            workbook = writer.book
            
            # Add formats
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#1E88E5',
                'font_color': 'white',
                'border': 1
            })
            
            number_format = workbook.add_format({
                'num_format': '#,##0.00',
                'border': 1
            })
            
            percent_format = workbook.add_format({
                'num_format': '0.00%',
                'border': 1
            })

            # Write Raw Data sheet
            df.to_excel(writer, sheet_name='Raw Data', index=False)
            worksheet = writer.sheets['Raw Data']
            format_worksheet(worksheet, df, header_format, number_format)

            # Create and write sheets based on report type
            if report_type == "Sales Summary":
                # Sales Trend Data
                sales_trend = df.groupby("InvoiceDate")["TotalSales"].sum().reset_index()
                sales_trend.to_excel(writer, sheet_name='Sales Trend', index=False)
                format_worksheet(writer.sheets['Sales Trend'], sales_trend, header_format, number_format)

                # Top Retailers Data
                top_retailers = df.groupby("Retailer").agg({
                    "TotalSales": "sum",
                    "UnitsSold": "sum",
                    "OperatingProfit": "sum"
                }).reset_index().sort_values("TotalSales", ascending=False)
                top_retailers.to_excel(writer, sheet_name='Top Retailers', index=False)
                format_worksheet(writer.sheets['Top Retailers'], top_retailers, header_format, number_format)

                # Sales Method Distribution
                sales_method = df.groupby("SalesMethod").agg({
                    "TotalSales": "sum",
                    "UnitsSold": "sum",
                    "OperatingProfit": "sum"
                }).reset_index()
                sales_method.to_excel(writer, sheet_name='Sales by Method', index=False)
                format_worksheet(writer.sheets['Sales by Method'], sales_method, header_format, number_format)

            elif report_type == "Product Performance":
                # Product Metrics
                product_metrics = df.groupby("Product").agg({
                    "TotalSales": "sum",
                    "UnitsSold": "sum",
                    "OperatingProfit": "sum",
                    "OperatingMargin": "mean"
                }).reset_index()
                product_metrics.to_excel(writer, sheet_name='Product Metrics', index=False)
                format_worksheet(writer.sheets['Product Metrics'], product_metrics, header_format, number_format)

                # Top Products
                top_products = product_metrics.sort_values("TotalSales", ascending=False).head(10)
                top_products.to_excel(writer, sheet_name='Top Products', index=False)
                format_worksheet(writer.sheets['Top Products'], top_products, header_format, number_format)

                # Product Profitability
                product_profitability = product_metrics[["Product", "TotalSales", "OperatingMargin", "UnitsSold"]]
                product_profitability.to_excel(writer, sheet_name='Product Profitability', index=False)
                format_worksheet(writer.sheets['Product Profitability'], product_profitability, header_format, number_format)

            else:  # Regional Analysis
                # Regional Metrics
                regional_metrics = df.groupby(["Region", "State"]).agg({
                    "TotalSales": "sum",
                    "UnitsSold": "sum",
                    "OperatingProfit": "sum"
                }).reset_index()
                regional_metrics.to_excel(writer, sheet_name='Regional Metrics', index=False)
                format_worksheet(writer.sheets['Regional Metrics'], regional_metrics, header_format, number_format)

                # Region Sales
                region_sales = regional_metrics.groupby("Region")["TotalSales"].sum().reset_index()
                region_sales.to_excel(writer, sheet_name='Sales by Region', index=False)
                format_worksheet(writer.sheets['Sales by Region'], region_sales, header_format, number_format)

                # State Performance
                state_metrics = df.groupby("State").agg({
                    "TotalSales": "sum",
                    "UnitsSold": "sum",
                    "OperatingProfit": "sum"
                }).reset_index()
                state_metrics.to_excel(writer, sheet_name='State Performance', index=False)
                format_worksheet(writer.sheets['State Performance'], state_metrics, header_format, number_format)

                # City Performance
                city_metrics = df.groupby("City")["TotalSales"].sum().reset_index()
                top_cities = city_metrics.sort_values("TotalSales", ascending=False)
                top_cities.to_excel(writer, sheet_name='City Performance', index=False)
                format_worksheet(writer.sheets['City Performance'], top_cities, header_format, number_format)

            # Add Summary sheet with key metrics
            summary_data = pd.DataFrame({
                'Metric': [
                    'Total Sales',
                    'Total Units Sold',
                    'Average Sale Value',
                    'Total Operating Profit',
                    'Average Operating Margin',
                    'Number of Transactions',
                    'Date Range',
                    'Report Type'
                ],
                'Value': [
                    f"${df['TotalSales'].sum():,.2f}",
                    f"{df['UnitsSold'].sum():,}",
                    f"${df['TotalSales'].mean():,.2f}",
                    f"${df['OperatingProfit'].sum():,.2f}",
                    f"{(df['OperatingProfit'].sum() / df['TotalSales'].sum() * 100):.2f}%",
                    f"{len(df):,}",
                    f"{df['InvoiceDate'].min().strftime('%Y-%m-%d')} to {df['InvoiceDate'].max().strftime('%Y-%m-%d')}",
                    report_type
                ]
            })
            summary_data.to_excel(writer, sheet_name='Summary', index=False)
            format_worksheet(writer.sheets['Summary'], summary_data, header_format, number_format)

        # Generate the download link
        output.seek(0)
        current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"{report_type.lower().replace(' ', '_')}_{current_time}.xlsx"
        
        st.download_button(
            label="📥 Download Excel Report",
            data=output,
            file_name=file_name,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
        st.success("Report generated successfully!")
        
    except Exception as e:
        st.error(f"Error generating Excel report: {str(e)}")

def format_worksheet(worksheet, df, header_format, number_format):
    """Helper function to format worksheet headers and columns."""
    # Format headers
    for col_num, value in enumerate(df.columns.values):
        worksheet.write(0, col_num, value, header_format)
    
    # Adjust column widths
    for i, col in enumerate(df.columns):
        max_length = max(df[col].astype(str).apply(len).max(), len(str(col)))
        worksheet.set_column(i, i, max_length + 2)
        
        # Apply number format to numeric columns
        if df[col].dtype in ['float64', 'int64']:
            for row in range(1, len(df) + 1):
                worksheet.write_number(row, i, df[col].iloc[row-1], number_format)

def export_to_csv(df, report_type):
    """Export the filtered data to CSV."""
    try:
        # Convert dataframe to CSV
        csv = df.to_csv(index=False)
        
        # Generate the download link
        current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"{report_type.lower().replace('', '_')}_{current_time}.csv"
        
        st.download_button(
            label="📥 Download CSV Report",
            data=csv,
            file_name=file_name,
            mime="text/csv"
        )
        
        st.success("Report generated successfully!")
        
    except Exception as e:
        st.error(f"Error generating CSV report: {str(e)}")
    
if __name__ == "__main__":
    main()
