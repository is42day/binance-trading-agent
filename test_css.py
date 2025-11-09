#!/usr/bin/env python3
"""
Quick CSS debugging - test metric card styling
"""
import streamlit as st

st.set_page_config(page_title="CSS Test", layout="wide")

# Add comprehensive CSS
st.markdown("""
<style>
/* AGGRESSIVE CSS OVERRIDE FOR METRIC CARDS */

/* Target all possible metric selectors */
[data-testid="metric-container"],
.metric-container,
.stMetric,
div[class*="metric"],
[class*="MetricBlock"],
[class*="metric-block"] {
    background: #2f3035 !important;
    border: 1px solid rgba(255, 145, 77, 0.3) !important;
    border-radius: 8px !important;
    padding: 16px !important;
    min-height: 120px !important;
    height: 120px !important;
    max-height: 120px !important;
    display: flex !important;
    flex-direction: column !important;
    justify-content: space-between !important;
}

[data-testid="metric-container"]:hover,
.metric-container:hover {
    background: #353a3f !important;
    border-color: rgba(255, 145, 77, 0.6) !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 4px 12px rgba(255, 145, 77, 0.3) !important;
}

/* Specific targeting for Streamlit metric internals */
.css-1px2l00e, 
div[class*="css-"] {
    height: auto !important;
}

/* Make sure labels and values position correctly */
[data-testid="metric-container"] * {
    box-sizing: border-box !important;
}

</style>
""", unsafe_allow_html=True)

st.title("🧪 CSS Test - Metric Card Styling")
st.write("Testing if metric cards will be styled with 120px height...")

# Create test metrics
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Test 1", "100", "+5%")

with col2:
    st.metric("Test 2", "200", "-3%")

with col3:
    st.metric("Test 3", "150", "0%")

with col4:
    st.metric("Test 4", "250", "+10%")

st.markdown("---")

st.subheader("Inspect the cards above:")
st.write("""
1. **Check card heights** - Should all be exactly the same
2. **Check alignment** - All cards should be at same vertical level
3. **Check hover effect** - Hover over a card, should lift up 2px
4. **View page source** - Right click → View Page Source, search for 'metric-container'
""")
