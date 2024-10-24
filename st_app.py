import streamlit as st
import pandas as pd
import xml.etree.ElementTree as ET
import plotly.express as px
from src.api.routes import convert_to_odata, insights_generation, ConversationManager, Query  # Adjust import based on your structure

if 'data' not in st.session_state:
    st.session_state['data'] = None

if 'query_history' not in st.session_state:
    st.session_state['query_history'] = []

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
    st.title("Smart Reporting Bot")
    st.markdown("""
        Introducing our AI-based application QueryOData that simplifies data access by transforming natural language queries into OData queries.
    """)

# Creating tabs for different functionalities
tab1, tab2, tab3, tab4 = st.tabs(["Query Point", "Insights", "Graphical Visualizations", "Query History"])

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
        submit_button = st.button("Execute Query", use_container_width=True)
    with col2:
        clear_button = st.button("Clear", use_container_width=True)

    if submit_button:
        if not query_input:
            st.error("⚠️ Please enter a query before submitting.")
        else:
            # Show a spinner while processing
            st.session_state['query_history'].append(query_input)
            with st.spinner("Processing query..."):
                try:
                    # Get the XML response as a string
                    xml_data = get_response(query_input)
                    
                    if xml_data:
                        dataframe = parse_xml_to_dataframe(xml_data)
                        
                        if dataframe is not None and not dataframe.empty:
                            # Success message
                            st.success("✅ Query executed successfully!")
                            st.session_state['last_dataframe'] = dataframe
                            st.write("✅ Stored the new dataframe into memory!")
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
                                label="Download Results as CSV",
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
    st.subheader("AI Insights")

    # Input field for the AI prompt
    ai_prompt = st.text_area(
        "Ask the AI for insights about the data:",
        value="",
        height=80,
        placeholder="Example: What trends can you identify from this data?",
        help="Enter your question or prompt for the AI here."
    )
    manager = ConversationManager(max_history=3)
    # Button to submit the AI prompt
    if st.button("Get AI Insights"):
        if not ai_prompt:
            st.error("⚠️ Please enter a prompt before submitting.")
        else:
            st.session_state['query_history'].append(ai_prompt)
            # Assuming 'last_dataframe' is available in session state
            if 'last_dataframe' in st.session_state and st.session_state['last_dataframe'] is not None:
                # Show a spinner while processing
                with st.spinner("🧠 Asking AI for insights..."):
                    
                    ai_response = insights_generation(prompt=ai_prompt, df=st.session_state['last_dataframe'], conversation_manager=manager)
                    # Display AI insights with improved layout
                    st.subheader("AI Insights")
                    # Check if there's reasoning and code to display
                    if ai_response.get("reasoning") or ai_response.get("code") or ai_response.get("output"):
                    # Create a card-style container for the insights
                        with st.container():
                        # Show reasoning in an expandable section if it exists
                            if ai_response.get("reasoning"):
                                with st.expander("Reasoning (click to expand)", expanded=False):
                                    st.write(ai_response.get("reasoning"))

                            # Show code in an expandable section if it exists
                            if ai_response.get("code"):
                                with st.expander("Code (click to expand)", expanded=False):
                                    st.code(ai_response.get("code"))

                            # Show the output in a prominent section
                            if ai_response.get("output"):
                                st.markdown("### Result", unsafe_allow_html=True)  # Add a header for the result
                                st.success(ai_response.get("output"))  # Display output in a success message style

                        # Handle the case where no insights are available
                    else:
                        st.warning("No insights were generated. Please check your input or try again.")

with tab3:
    if 'last_dataframe' in st.session_state and st.session_state['last_dataframe'] is not None:
        st.subheader("Chart")

        # Initialize chart settings in session state
        if 'chart_type' not in st.session_state:
            st.session_state['chart_type'] = 'Line'
        if 'x_col' not in st.session_state:
            st.session_state['x_col'] = None
        if 'y_cols' not in st.session_state:
            st.session_state['y_cols'] = []

        # Display chart options inside the tab (instead of sidebar)
        st.header('Chart Options')

        # Chart type selection
        chart_type = st.selectbox('Select chart type:', [
            'Line', 'Bar', 'Stacked Bar', 'Grouped Bar', 'Horizontal Bar', 'Scatter', 'Histogram', 'Pie', 'Box', 'Heatmap', 'Violin', 'Sunburst', 'Bubble', 'Area', 'Radar', 'Funnel', 'Density', 'Contour', 'Treemap'])
        st.session_state['chart_type'] = chart_type

        # Select x-axis column inside the tab
        x_col = st.selectbox('Select x-axis column:', st.session_state['last_dataframe'].columns, 
                             index=list(st.session_state['last_dataframe'].columns).index(st.session_state['x_col']) if st.session_state['x_col'] else 0)
        st.session_state['x_col'] = x_col

        # Filter y-axis columns to exclude the selected x-axis column
        y_options = [col for col in st.session_state['last_dataframe'].columns if col != st.session_state['x_col']]

        # Select y-axis columns inside the tab
        y_cols = st.multiselect('Select y-axis columns:', y_options, default=st.session_state['y_cols'])
        st.session_state['y_cols'] = y_cols

        # Initialize the figure
        fig = None
        if len(st.session_state['y_cols']) > 0:
            if st.session_state['chart_type'] == 'Line':
                fig = px.line(st.session_state['last_dataframe'], x=st.session_state['x_col'], y=st.session_state['y_cols'])
            elif st.session_state['chart_type'] == 'Bar':
                fig = px.bar(st.session_state['last_dataframe'], x=st.session_state['x_col'], y=st.session_state['y_cols'])
            elif st.session_state['chart_type'] == 'Stacked Bar':
                fig = px.bar(st.session_state['last_dataframe'], x=st.session_state['x_col'], y=st.session_state['y_cols'], text_auto=True)
                fig.update_layout(barmode='stack')
            elif st.session_state['chart_type'] == 'Grouped Bar':
                fig = px.bar(st.session_state['last_dataframe'], x=st.session_state['x_col'], y=st.session_state['y_cols'], text_auto=True)
                fig.update_layout(barmode='group')

        # Render the figure if created
        if fig:
            st.plotly_chart(fig)
    else:
        st.write("No data available to generate the chart.")


with tab4:
    st.subheader("Recent Queries")
    if st.session_state["query_history"] is not None:
        for query in st.session_state["query_history"]:
            st.write(query)
    # Here you could implement query history functionality"

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
