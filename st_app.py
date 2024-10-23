import streamlit as st
import pandas as pd
import xml.etree.ElementTree as ET
import requests
from pydantic import BaseModel
from src.api.routes import convert_to_odata, Query  # Adjust import based on your structure
from datetime import datetime


def get_response(query_input: str):
    try:
        query = Query(text=query_input)
        # Call the FastAPI endpoint to get the XML response
        xml_response = convert_to_odata(query)
        print(type(xml_response.body))
        return xml_response.body  # Return the raw XML response text
    except Exception as e:
        print(f"An error occurred: {e}")
        st.error("Failed to fetch the response from the server.")
        return None

def parse_xml_to_dataframe(xml_data: str):
    try:
        # Parse the XML string directly
        root = ET.fromstring(xml_data)
        all_records = []
        
        # Adjust the namespace accordingly based on your XML structure
        for record in root.findall(".//{http://www.w3.org/2005/Atom}entry"):
            fields = {}
            properties = record.find(".//{http://schemas.microsoft.com/ado/2007/08/dataservices/metadata}properties")
            if properties is not None:
                for field in properties:
                    tag = field.tag.split('}')[1]  # Get the field name without the namespace
                    value = field.text if field.text is not None else ""  # Handle None values
                    fields[tag] = value  
            all_records.append(fields)

        return pd.DataFrame(all_records)
    except Exception as e:
        print(f"Error has occurred while executing: {e}")
        st.error("Error parsing the XML data.")
        return None




# Set page configuration
st.set_page_config(
    page_title="Smart OData Assistant",
    page_icon="🔍",
    layout="wide"
)

# Custom CSS to inject
st.markdown("""
    <style>
    .main {
        padding: 0rem 1rem;
    }
    .stButton > button {
        width: 100%;
        margin-top: 0.5rem;
    }
    .reportview-container .main .block-container {
        max-width: 95%;
        padding-top: 1rem;
        padding-bottom: 1rem;
    }
    div[data-testid="stDataFrame"] > div {
        width: 100%;
    }
    /* Reduce header spacing */
    h1 {
        margin-top: -1rem;
        margin-bottom: 0;
        padding-bottom: 0;
        font-size: 1.8rem !important;
    }
    /* Reduce tab padding */
    .stTabs [data-baseweb="tab-list"] {
        gap: 1rem;
        padding-bottom: 0;
    }
    .stTabs [data-baseweb="tab"] {
        padding-top: 0;
    }
    /* Compact description */
    .small-text {
        font-size: 0.9rem;
        margin-bottom: 0.5rem;
    }
    </style>
""", unsafe_allow_html=True)

# Header section with title and description
col1, col2 = st.columns([6,1])
with col1:
    st.title("🔍 Smart QueryOData Assistant")
    st.markdown("""
        Introducing our AI-based application QueryOData that simplifies data access by transforming natural language queries into OData queries.
    """)

# Creating tabs for different functionalities
tab1, tab2 = st.tabs(["Query Point", "Query History"])

with tab1:
    # Query input section
    st.subheader("Query Input")
    query_input = st.text_area(
        "Enter your query below:",
        value="",
        height=80,
        placeholder="Example: Show total orders by supplier, Find orders from supplier ABC created in 2023",
        help="Enter your OData query here. Use standard OData syntax."
    )

    col1, col2 = st.columns([1,1])
    with col1:
        submit_button = st.button("📤 Execute Query", use_container_width=True)
    with col2:
        clear_button = st.button("🗑️ Clear", use_container_width=True)

    if submit_button:
        if not query_input:
            st.error("⚠️ Please enter a query before submitting.")
        else:
            # Show a spinner while processing
            with st.spinner("🔍Processing query..."):
                try:
                    # Get the XML response as a string
                    xml_data = get_response(query_input)
                    
                    if xml_data:
                        dataframe = parse_xml_to_dataframe(xml_data)
                        
                        if dataframe is not None and not dataframe.empty:
                            # Success message
                            st.success("✅ Query executed successfully!")
                            
                            # Display metrics
                            col1, col2 = st.columns(2)
                            with col1:
                                st.metric("Total Records", len(dataframe))
                            with col2:
                                st.metric("Columns", len(dataframe.columns))
                            
                            # Display the dataframe with expanded width
                            st.subheader("Query Results")
                            st.dataframe(
                                dataframe,
                                use_container_width=True,
                                height=400
                            )
                            
                            # Download button for the results
                            csv = dataframe.to_csv(index=False)
                            st.download_button(
                                label="📥 Download Results as CSV",
                                data=csv,
                                file_name="query_results.csv",
                                mime="text/csv",
                                use_container_width=True
                            )
                        else:
                            st.warning("📝 No data available to display. Please Check your Query")
                except Exception as e:
                    st.error(f"❌ An error occurred: {str(e)}")
                    st.exception(e)  # This will show the full error trace in a collapsible section

with tab2:
    st.subheader("Recent Queries")
    # Here you could implement query history functionality
    st.info("Query history feature coming soon! This will show your recent queries and their results.")

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center'>
        <p>Need help? Check out our 
        <a href='#' target='_blank'>documentation</a> or 
        <a href='#' target='_blank'>contact support</a>.</p>
    </div>
    """,
    unsafe_allow_html=True
)