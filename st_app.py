import streamlit as st
import pandas as pd
import plotly.express as px
from src.api.routes import convert_to_odata, Query  # Adjust import based on your structure
from src.api.routes import insights_generation, ConversationManager


if 'data' not in st.session_state:
    st.session_state['data'] = None
if 'show_results' not in st.session_state:
    st.session_state.show_results = False
if 'query_history' not in st.session_state:
    st.session_state['query_history'] = []
if 'count' not in st.session_state:
    st.session_state['count'] = None


def get_response(query_input: str):
    try:
        query = Query(text=query_input)
        # to get a DICTIONARY RESPONSE
        values = convert_to_odata(query)
        return values
    except Exception as e:
        print(f"An error occurred: {e}")
        st.error("Failed to fetch the response from the server.")
        return None

def parse_list_to_dataframe(list_data):
    try:
        # Convert the list of records to a DataFrame
        df = pd.DataFrame(list_data)
        return df
    
    except Exception as e:
        print(f"An error occurred: {e}")
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
tab1, tab2, tab3, tab4 = st.tabs(["Query Point", "Insights", "Graphical Visualization","Query History"])

with tab1:
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
        if st.button("Execute Query", use_container_width=True):
            if not query_input:
                st.error("⚠️ Please enter a query before submitting.")
            else:
                with st.spinner("Processing query..."):
                    try:
                        
                        list_response = get_response(query_input)
                        
                        if list_response:
                            dataframe = parse_list_to_dataframe(list_response)
                            # if count is not None:
                            #     st.session_state['count'] = count
                            if dataframe is not None and not dataframe.empty:
                                st.success("✅ Query executed successfully!")
                                # Store results in session state
                                st.session_state.last_dataframe = dataframe
                                st.session_state.show_results = True
                                st.write("✅ Stored the new dataframe into memory!")
                            else:
                                st.warning("📝 No data available to display. Please Check your Query")
                    except Exception as e:
                        st.error(f"❌ An error occurred: {str(e)}")
                        st.exception(e)
    
    with col2:
        if st.button("Clear", use_container_width=True):
            st.session_state.show_results = False
            st.session_state.last_dataframe = None
            st.rerun()

    # Display results if they exist
    if st.session_state.show_results and st.session_state.last_dataframe is not None:
        num_rows, num_cols = st.session_state.last_dataframe.shape
       
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Number of Rows")
            st.markdown(f"<h3 style='color: #4A4A4A;'>Number of Rows: <b>{num_rows}</b></h3>", unsafe_allow_html=True)
            
        with col2:
            st.subheader("Number of Columns")
            st.markdown(f"<h3 style='color: #4A4A4A;'>Number of Columns: <b>{num_cols}</b></h3>", unsafe_allow_html=True)
        
        st.subheader("Query Results")
        st.dataframe(
            st.session_state.last_dataframe.head(200),
            use_container_width=True,
            height=400
        )

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
                                with st.expander("### Reasoning (click to expand)", expanded=False):
                                    st.write(ai_response.get("reasoning"))

                            # Show code in an expandable section if it exists
                            if ai_response.get("code"):
                                with st.expander("### Code (click to expand)", expanded=False):
                                    st.code(ai_response.get("code"))

                            # Show the output in a prominent section
                            output = ai_response.get("output")
                            if output:
                                try:
                                    output_df = pd.DataFrame(output)
                                    st.markdown("### Result", unsafe_allow_html=True)
                                    st.dataframe(output_df)
                                    #if ai_response.get("output"):
                                    #    st.markdown("### Result", unsafe_allow_html=True)  # Add a header for the result
                                    #   st.success(ai_response.get("output"))  # Display output in a success message style
                                except ValueError:
                                    st.markdown("### Result", unsafe_allow_html=True)
                                    st.success(output)

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
