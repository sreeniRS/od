import streamlit as st
import pandas as pd
import xml.etree.ElementTree as ET
import requests
from pydantic import BaseModel
from src.api.routes import convert_to_odata, Query  # Adjust import based on your structure

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

# Streamlit frontend
st.title("OData Query Assistant")

# User input for the query
query_input = st.text_area("Enter your query", value="", height=20)

if st.button("Submit"):
    st.write("Checking if query")
    if not query_input:
        st.error("Query has not been entered")
    else:
        try:
            # Get the XML response as a string
            xml_data = get_response(query_input)
            if xml_data:  # Check if xml_data is not None
                dataframe = parse_xml_to_dataframe(xml_data)
                if dataframe is not None and not dataframe.empty:
                    st.write("### Query Results")
                    st.dataframe(dataframe)
                else:
                    st.warning("No data available to display.")
        except Exception as e:
            print(f"An exception was thrown: {e}")
            st.error(f"An error occurred: {e}")


