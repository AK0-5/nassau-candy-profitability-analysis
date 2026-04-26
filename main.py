import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os

st.set_page_config(page_title="Nassau Candy Profitability", layout="wide")

#csv_path = os.path.join(os.path.dirname(__file__), "data", "Nassau Candy Distributor.csv")
csv_path = "C:/Users/DELL/PycharmProjects/NassauDashboard/Nassau Candy Distributor.csv"

@st.cache_data
def load_data():
    df = pd.read_csv(csv_path)

    df['Order Date'] = pd.to_datetime(df['Order Date'], format='%d-%m-%Y', errors='coerce')

    df['Gross Margin %'] = (df['Gross Profit'] / df['Sales'] * 100).round(2)
    df['Profit per Unit'] = df['Gross Profit'] / df['Units']

    return df

df = load_data()

with st.sidebar:
    st.header("Filters")

    date_range = st.date_input(
        "Order date range",
        value=(df['Order Date'].min().date(), df['Order Date'].max().date())
    )

    divisions = sorted(df['Division'].unique())
    selected_div = st.multiselect("Division", divisions, default=divisions)

    min_margin = st.slider("Minimum Margin %", 0, 100, 35)

    prod_search = st.text_input("Search Product")

f_df = df.copy()

if len(date_range) == 2:
    f_df = f_df[
        (f_df['Order Date'].dt.date >= date_range[0]) &
        (f_df['Order Date'].dt.date <= date_range[1])
    ]

if selected_div:
    f_df = f_df[f_df['Division'].isin(selected_div)]

f_df = f_df[f_df['Gross Margin %'] >= min_margin]

if prod_search:
    f_df = f_df[f_df['Product Name'].str.contains(prod_search, case=False, na=False)]

# KPI's
total_sales = f_df['Sales'].sum()
total_profit = f_df['Gross Profit'].sum()
total_units = f_df['Units'].sum()

margin = (total_profit / total_sales * 100) if total_sales > 0 else 0
ppu = (total_profit / total_units) if total_units > 0 else 0

col1, col2, col3, col4, col5 = st.columns(5)

col1.metric("Total Sales", f"${total_sales:,.0f}")
col2.metric("Total Profit", f"${total_profit:,.0f}")
col3.metric("Gross Margin %", f"{margin:.1f}%")
col4.metric("Profit per Unit", f"${ppu:.2f}")
col5.metric("Total Records", len(f_df))

st.markdown("---")

tab1, tab2, tab3, tab4 = st.tabs([
    "Product Overview",
    "Division Performance",
    "Cost Diagnostics",
    "Pareto Analysis"
])

# Product Overview
with tab1:

    prod = f_df.groupby(['Product Name', 'Division']).agg({
        'Sales': 'sum',
        'Gross Profit': 'sum',
        'Gross Margin %': 'mean'
    }).reset_index()

    prod['Revenue Contribution %'] = (prod['Sales'] / total_sales * 100) if total_sales > 0 else 0
    prod['Profit Contribution %'] = (prod['Gross Profit'] / total_profit * 100) if total_profit > 0 else 0

    k1, k2 = st.columns(2)
    k1.metric("Top Revenue Contribution", f"{prod['Revenue Contribution %'].max():.1f}%")
    k2.metric("Top Profit Contribution", f"{prod['Profit Contribution %'].max():.1f}%")

    c1, c2 = st.columns(2)

    with c1:
        fig1 = px.bar(
            prod.nlargest(10, 'Gross Profit'),
            x='Product Name',
            y='Gross Profit',
            title="Top Products by Profit"
        )
        st.plotly_chart(fig1, use_container_width=True)

    with c2:
        fig2 = px.bar(
            prod.nlargest(10, 'Gross Margin %'),
            x='Product Name',
            y='Gross Margin %',
            title="Top Products by Margin"
        )
        st.plotly_chart(fig2, use_container_width=True)

# Division Performance
with tab2:

    div = f_df.groupby('Division').agg({
        'Sales': 'sum',
        'Gross Profit': 'sum',
        'Gross Margin %': 'mean'
    }).reset_index()

    fig = px.bar(
        div,
        x='Division',
        y=['Sales', 'Gross Profit'],
        barmode='group',
        title="Revenue vs Profit by Division"
    )
    st.plotly_chart(fig, use_container_width=True)

    fig2 = px.box(
        f_df,
        x='Division',
        y='Gross Margin %',
        title="Margin Distribution by Division"
    )
    st.plotly_chart(fig2, use_container_width=True)

# Cost Diagnostics
with tab3:

    agg = f_df.groupby('Product Name').agg({
        'Sales': 'sum',
        'Cost': 'sum',
        'Gross Profit': 'sum',
        'Gross Margin %': 'mean'
    }).reset_index()

    agg['Category'] = agg.apply(
        lambda x: "High Sales / Low Margin"
        if x['Sales'] > agg['Sales'].median() and x['Gross Margin %'] < min_margin
        else "Others",
        axis=1
    )

    agg['Action'] = agg.apply(
        lambda x: "Reprice"
        if x['Gross Margin %'] < min_margin else "Healthy",
        axis=1
    )

    fig = px.scatter(
        agg,
        x='Sales',
        y='Cost',
        size='Gross Profit',
        color='Category',
        hover_name='Product Name',
        title="Cost vs Sales (High Risk Highlighted)"
    )
    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(
        agg[['Product Name', 'Gross Margin %', 'Category', 'Action']],
        use_container_width=True
    )

# Pareto Analysis
with tab4:

    # Profit Pareto
    pareto_profit = f_df.groupby('Product Name')['Gross Profit'].sum().sort_values(ascending=False).reset_index()
    pareto_profit['cum_%'] = pareto_profit['Gross Profit'].cumsum() / pareto_profit['Gross Profit'].sum() * 100

    fig1 = go.Figure()
    fig1.add_bar(x=pareto_profit['Product Name'][:10], y=pareto_profit['Gross Profit'][:10], name="Profit")
    fig1.add_scatter(
        x=pareto_profit['Product Name'][:10],
        y=pareto_profit['cum_%'][:10],
        name="Cumulative %",
        yaxis="y2"
    )
    fig1.update_layout(
        title="Profit Pareto",
        yaxis2=dict(overlaying='y', side='right', range=[0, 110])
    )
    st.plotly_chart(fig1, use_container_width=True)

    # Revenue Pareto
    pareto_sales = f_df.groupby('Product Name')['Sales'].sum().sort_values(ascending=False).reset_index()
    pareto_sales['cum_%'] = pareto_sales['Sales'].cumsum() / pareto_sales['Sales'].sum() * 100

    fig2 = go.Figure()
    fig2.add_bar(x=pareto_sales['Product Name'][:10], y=pareto_sales['Sales'][:10], name="Sales")
    fig2.add_scatter(
        x=pareto_sales['Product Name'][:10],
        y=pareto_sales['cum_%'][:10],
        name="Cumulative %",
        yaxis="y2"
    )
    fig2.update_layout(
        title="Revenue Pareto",
        yaxis2=dict(overlaying='y', side='right', range=[0, 110])
    )
    st.plotly_chart(fig2, use_container_width=True)

    # Dependency Insights
    if len(pareto_profit) >= 5:
        top3 = pareto_profit['cum_%'].iloc[2]
        top5 = pareto_profit['cum_%'].iloc[4]
        top10 = pareto_profit['cum_%'].iloc[9] if len(pareto_profit) >= 10 else 100
        sku80 = (pareto_profit['cum_%'] <= 80).sum()

        st.markdown(f"""
        ### 📊 Key Dependency Insights
        - Top 3 products contribute **{top3:.1f}%** of total profit  
        - Top 5 products contribute **{top5:.1f}%** of total profit  
        - Top 10 products contribute **{top10:.1f}%** of total profit  
        - Around **80% of profit comes from {sku80} products**
        """)