import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ─── PAGE CONFIG ─────────────────────────────────────
st.set_page_config(page_title="Nassau Candy Profitability", layout="wide")

st.title("Nassau Candy Distributor – Profitability & Margin Analysis")
st.caption("Product-level profit, margin, and cost performance dashboard")

# ─── LOAD DATA ───────────────────────────────────────
@st.cache_data
def load_data():
    df = pd.read_csv("Nassau Candy Distributor.csv")

    # Convert date
    df['Order Date'] = pd.to_datetime(df['Order Date'], format='%d-%m-%Y', errors='coerce')

    # Create metrics
    df['Gross Margin %'] = (df['Gross Profit'] / df['Sales'] * 100).round(2)
    df['Profit per Unit'] = df['Gross Profit'] / df['Units']

    return df

df = load_data()

# ─── SIDEBAR FILTERS ─────────────────────────────────
st.sidebar.header("Filters")

date_range = st.sidebar.date_input(
    "Select Date Range",
    value=(df['Order Date'].min().date(), df['Order Date'].max().date())
)

divisions = sorted(df['Division'].dropna().unique())
selected_div = st.sidebar.multiselect("Select Division", divisions, default=divisions)

min_margin = st.sidebar.slider("Minimum Margin %", 0, 100, 35)

product_search = st.sidebar.text_input("Search Product")

# ─── APPLY FILTERS ───────────────────────────────────
f_df = df.copy()

if len(date_range) == 2:
    f_df = f_df[
        (f_df['Order Date'].dt.date >= date_range[0]) &
        (f_df['Order Date'].dt.date <= date_range[1])
    ]

if selected_div:
    f_df = f_df[f_df['Division'].isin(selected_div)]

f_df = f_df[f_df['Gross Margin %'] >= min_margin]

if product_search:
    f_df = f_df[f_df['Product Name'].str.contains(product_search, case=False, na=False)]

# ─── KPIs ────────────────────────────────────────────
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

# ─── TABS ────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "Product Overview",
    "Division Performance",
    "Cost Diagnostics",
    "Pareto Analysis"
])

# ─── TAB 1: PRODUCT OVERVIEW ─────────────────────────
with tab1:
    st.subheader("Top Products by Profit & Margin")

    prod = f_df.groupby(['Product Name', 'Division']).agg({
        'Sales': 'sum',
        'Gross Profit': 'sum',
        'Gross Margin %': 'mean'
    }).reset_index()

    prod['Revenue Contribution %'] = (prod['Sales'] / total_sales * 100) if total_sales > 0 else 0
    prod['Profit Contribution %'] = (prod['Gross Profit'] / total_profit * 100) if total_profit > 0 else 0

    c1, c2 = st.columns(2)

    with c1:
        fig1 = px.bar(
            prod.nlargest(10, 'Gross Profit'),
            x='Product Name',
            y='Gross Profit',
            color='Division',
            title="Top 10 Products by Profit"
        )
        fig1.update_layout(xaxis_tickangle=45)
        st.plotly_chart(fig1, use_container_width=True)

    with c2:
        fig2 = px.bar(
            prod.nlargest(10, 'Gross Margin %'),
            x='Product Name',
            y='Gross Margin %',
            color='Division',
            title="Top 10 Products by Margin %"
        )
        fig2.update_layout(xaxis_tickangle=45)
        st.plotly_chart(fig2, use_container_width=True)

# ─── TAB 2: DIVISION PERFORMANCE ─────────────────────
with tab2:
    st.subheader("Division Performance")

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
        title="Revenue vs Profit"
    )
    st.plotly_chart(fig, use_container_width=True)

    fig2 = px.box(
        f_df,
        x='Division',
        y='Gross Margin %',
        title="Margin Distribution"
    )
    st.plotly_chart(fig2, use_container_width=True)

# ─── TAB 3: COST DIAGNOSTICS ─────────────────────────
with tab3:
    st.subheader("Cost vs Sales Analysis")

    agg = f_df.groupby('Product Name').agg({
        'Sales': 'sum',
        'Cost': 'sum',
        'Gross Profit': 'sum',
        'Gross Margin %': 'mean'
    }).reset_index()

    agg['Category'] = agg.apply(
        lambda x: "High Sales / Low Margin"
        if x['Sales'] > agg['Sales'].median() and x['Gross Margin %'] < min_margin
        else "Normal",
        axis=1
    )

    fig = px.scatter(
        agg,
        x='Sales',
        y='Cost',
        size='Gross Profit',
        color='Category',
        hover_name='Product Name',
        title="Cost vs Sales Scatter"
    )
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Margin Risk Products")
    risk = agg[agg['Gross Margin %'] < min_margin]

    if risk.empty:
        st.success("No low-margin products found")
    else:
        st.dataframe(risk[['Product Name', 'Sales', 'Cost', 'Gross Profit', 'Gross Margin %']])

# ─── TAB 4: PARETO ANALYSIS ──────────────────────────
with tab4:
    st.subheader("Profit Contribution (Pareto)")

    pareto = f_df.groupby('Product Name')['Gross Profit'].sum().sort_values(ascending=False).reset_index()
    pareto['cum_%'] = pareto['Gross Profit'].cumsum() / pareto['Gross Profit'].sum() * 100

    fig = go.Figure()
    fig.add_bar(x=pareto['Product Name'][:10], y=pareto['Gross Profit'][:10], name="Profit")
    fig.add_scatter(x=pareto['Product Name'][:10], y=pareto['cum_%'][:10],
                    name="Cumulative %", yaxis="y2")

    fig.update_layout(
        title="Top Products Profit Contribution",
        yaxis2=dict(overlaying='y', side='right')
    )

    st.plotly_chart(fig, use_container_width=True)

    # Insight
    if len(pareto) >= 5:
        top5 = pareto['cum_%'].iloc[4]
        st.info(f"Top 5 products contribute ~{top5:.1f}% of total profit")

# ─── DOWNLOAD BUTTON ─────────────────────────────────
st.markdown("---")

if not f_df.empty:
    st.download_button(
        "Download Filtered Data",
        f_df.to_csv(index=False).encode('utf-8'),
        file_name="filtered_data.csv",
        mime="text/csv"
    )