import streamlit as st  # Import Streamlit library
import pandas as pd     # Import pandas for data manipulation
import plotly.express as px  # Import Plotly Express for plotting

def PalayProduction():
    from data.Dashboard_Ready import provincial_df, municipality_df, supply_df

    # =========================
    # GET LATEST YEAR DYNAMICALLY
    # =========================
    latest_year = provincial_df["date"].dt.year.max()

    # Filter only latest year (instead of hardcoded 2025)
    provincial_latest = provincial_df[
        provincial_df["date"].dt.year == latest_year
        ].copy()

    # Sort by date
    provincial_latest = provincial_latest.sort_values("date")

    # Latest row for reference
    latest = provincial_latest.iloc[-1]


    # =========================
    # PROVINCIAL PREP
    # =========================
    df = provincial_df.copy()
    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month
    df["month_name"] = df["date"].dt.strftime("%b")

    # =========================
    # MUNICIPAL PREP
    # =========================
    mf = municipality_df.copy()
    mf["year"] = mf["date"].dt.year

    # =========================
    # SUPPLY PREP
    # =========================
    sr = supply_df.copy()
    sr["year"] = sr["date"].dt.year

    # Define colors for charts
    colors = ["#388e3c", "#FFEE58"]

    # -----------------------------
    # FORECAST CALCULATION
    # -----------------------------
    forecast_months = pd.date_range(
        start=latest["date"] + pd.DateOffset(months=1),
        periods=3,
        freq='MS'
    )

    next_month_name = forecast_months[0].strftime("%B %Y")

    # PAGE TITLE
    st.markdown(
        "<h2 style='text-align: center; color: #2E7D32; margin-top: -1rem;'>Palay Production</h2>",
        unsafe_allow_html=True
    )

    st.markdown(
        "<h2 style='text-align: left; color: black; font-size: 25px;'>Provincial Palay Production</h2>",
        unsafe_allow_html=True
    )

    # YEAR FILTER
    selected_years = st.multiselect(
        "Year Selection",
        options=sorted(df["year"].unique()),
        default=[df["year"].max()],
        help="Select one or more years"
    )

    if not selected_years:
        selected_years = [df["year"].max()]

    # Filter DataFrame
    pfiltered_df = df[df["year"].isin(selected_years)]

    # FIRST ROW: Production & Harvested
    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2, gap="large")

    # Production
    with col1:
        chart_title = f"Palay Production ({selected_years[0]})" if len(selected_years) == 1 else f"Palay Production ({min(selected_years)}–{max(selected_years)})"

        if len(selected_years) == 1:
            monthly = pfiltered_df.groupby("month")[["production_total"]].sum().reset_index() # Sum production by month
            monthly["month_name"] = monthly["month"].map({i: pd.to_datetime(i, format="%m").strftime("%b") for i in range(1, 13)}) # Add month names

            fig = px.bar(
                monthly, x="month_name", y="production_total",
                color_discrete_sequence=[colors[0]],
                text=monthly["production_total"].round(0).astype(int), # Show values on bars
                title=chart_title,
                template="plotly_white"
            )

            fig.update_layout(
                yaxis_title="Total Production",
                xaxis_title="Month",
            )

        else:
            annual = pfiltered_df.groupby("year")[["production_total"]].sum().reset_index() # Sum production by year

            fig = px.bar(
                annual, x="year", y="production_total",
                color_discrete_sequence=[colors[0]],
                text=annual["production_total"].round(0).astype(int),
                title=chart_title,
                template="plotly_white",

            )

            fig.update_layout (
                yaxis_title="Total Production",
                xaxis_title="Year",
            )

        fig.update_traces(texttemplate='%{text:,}', textposition='outside')
        st.plotly_chart(fig, width="stretch")

    # Harvested
    with col2:
        chart_title = f"Palay Harvested ({selected_years[0]})" if len(selected_years) == 1 else f"Palay Harvested ({min(selected_years)}–{max(selected_years)})"

        if len(selected_years) == 1: # Monthly harvested
            monthly = pfiltered_df.groupby("month")[["harvested_total"]].sum().reset_index()
            monthly["month_name"] = monthly["month"].map({i: pd.to_datetime(i, format="%m").strftime("%b") for i in range(1, 13)})

            fig = px.bar(
                monthly, x="month_name", y="harvested_total",
                color_discrete_sequence=[colors[1]],
                text=monthly["harvested_total"].round(0).astype(int),
                title=chart_title,
                template="plotly_white"
            )

            fig.update_layout(
                yaxis_title="Total Harvested",
                xaxis_title="Month",
            )
        else:
            annual = pfiltered_df.groupby("year")[["harvested_total"]].sum().reset_index()

            fig = px.bar(
                annual, x="year", y="harvested_total",
                color_discrete_sequence=[colors[1]],
                text=annual["harvested_total"].round(0).astype(int),
                title=chart_title,
                template="plotly_white"
            )

            fig.update_layout(
                yaxis_title="Total Harvested",
                xaxis_title="Year",
            )

        fig.update_traces(texttemplate='%{text:,}', textposition='outside')
        st.plotly_chart(fig, width="stretch")

    # SECOND ROW: Irrigated vs Rainfed
    col1, col2 = st.columns(2, gap="large")

    # Production Line
    with col1:
        if len(selected_years) == 1:
            data = pfiltered_df.groupby("month")[["production_irrigated", "harvested_irrigated"]].sum().reset_index()
            data["month_name"] = data["month"].map({i: pd.to_datetime(i, format="%m").strftime("%b")for i in range(1, 13)})
            x_val = "month_name"


        else:
            data = pfiltered_df.groupby("year")[["production_irrigated", "harvested_irrigated"]].sum().reset_index()
            x_val = "year"

        fig = px.line(
            data,
            x=x_val,
            y=["production_irrigated", "harvested_irrigated"],
            markers=True,
            color_discrete_map={
                "production_irrigated": colors[0],
                "harvested_irrigated": colors[1]
            },
            title= f"Comparison of Irrigated Production and Harvested Area ({selected_years[0]})" if len(selected_years) == 1 else f"Comparison of Irrigated Production and Harvested Area ({min(selected_years)}–{max(selected_years)})",
            template="plotly_white"
        )

        if len(selected_years) == 1:
            fig.update_layout(
                yaxis_title="Production",
                xaxis_title="Month",
                showlegend=True,
                legend=dict(
                    orientation="h",
                    y=-0.3,
                    x=0,
                    xanchor="left",
                    yanchor="top"
                ),
            )
        else:
            fig.update_layout(
                yaxis_title="Production",
                xaxis_title="Year",
                showlegend=True,
                legend=dict(
                    orientation="h",
                    y=-0.3,
                    x=0,
                    xanchor="left",
                    yanchor="top"
                ),
            )

        st.plotly_chart(fig, width="stretch")

    # Harvested Line
    with col2:
        if len(selected_years) == 1:
            data = pfiltered_df.groupby("month")[["production_rainfed", "harvested_rainfed"]].sum().reset_index()
            data["month_name"] = data["month"].map({i: pd.to_datetime(i, format="%m").strftime("%b") for i in range(1, 13)})
            x_val = "month_name"
        else:
            data = pfiltered_df.groupby("year")[["production_rainfed", "harvested_rainfed"]].sum().reset_index()
            x_val = "year"

        fig = px.line(
            data,
            x=x_val,
            y=["production_rainfed", "harvested_rainfed"],
            markers=True,
            color_discrete_map={
                "production_rainfed": colors[0],
                "harvested_rainfed": colors[1]
            },
            title=f"Comparison of Rainfed Production and Harvested Area ({selected_years[0]})" if len(selected_years) == 1 else f"Comparison of Rainfed Production and Harvested Area ({min(selected_years)}–{max(selected_years)})",
            template="plotly_white"
        )

        if len(selected_years) == 1:
            fig.update_layout(
                yaxis_title="Production",
                xaxis_title="Month",
                showlegend=True,
                legend=dict(
                    orientation="h",
                    y=-0.3,
                    x=0,
                    xanchor="left",
                    yanchor="top"
                ),
            )
        else:
            fig.update_layout(
                yaxis_title="Production",
                xaxis_title="Year",
                showlegend=True,
                legend=dict(
                    orientation="h",
                    y=-0.3,
                    x=0,
                    xanchor="left",
                    yanchor="top"
                ),
            )

        st.plotly_chart(fig, width="stretch")

    # THIRD ROW: YIELD

    if len(selected_years) == 1:
        yield_df = pfiltered_df.groupby("month")[["quarterly_yield_mt_per_ha"]].mean().reset_index()
        yield_df["month_name"] = yield_df["month"].map({i: pd.to_datetime(i, format="%m").strftime("%b") for i in range(1, 13)})
        x_val = "month_name"
    else:
        yield_df = pfiltered_df.groupby("year")[["quarterly_yield_mt_per_ha"]].mean().reset_index()
        x_val = "year"

    fig_yield = px.line(
        yield_df,
        x=x_val,
        y="quarterly_yield_mt_per_ha",
        markers=True,
        color_discrete_sequence=[colors[0]],
        title=f"Yield (tons per hectare) ({selected_years[0]})" if len(selected_years) == 1 else f"Yield (tons per hectare) ({min(selected_years)}–{max(selected_years)})",
        template="plotly_white"
    )

    if len (selected_years) == 1:
        fig_yield.update_layout(
            yaxis_title="Yield (tons per hectare)",
            xaxis_title="Month",
        )
    else:
        fig_yield.update_layout(
            yaxis_title="Yield (tons per hectare)",
            xaxis_title="Year",
        )

    st.plotly_chart(fig_yield,width="stretch")

    #END OF PROVINCIAL LEVEL
    st.markdown(
        '<hr style="border:1px solid black; margin:0px 0; margin-top: 15px;">',
        unsafe_allow_html=True
    )  # Divider before municipal section

    # Start of Municipal Level
    st.markdown(
        "<h2 style='text-align: left; color: black; font-size: 25px; margin-top: 30px;'>Municipal Palay Production</h2>",
        unsafe_allow_html=True
    ) # Title for municipal data

    # MUNICIPALITY SELECTION
    selected_municipality = st.multiselect(
        "Municipality Selection",
        options=sorted(mf["municipality"].unique()), # List all municipalities
        default=[mf["municipality"].iloc[0]],
        help="Select one or more municipalities"
    )

    #fallback
    if not selected_municipality:
        selected_municipality = [mf["municipality"].iloc[0]]

    # TITLE HANDLING
    all_muni = sorted(mf["municipality"].unique())

    if len(selected_municipality) == len(all_muni):
        title_muni = "All Municipalities"
    else:
        title_muni = ", ".join(selected_municipality)

    # FILTERED DATA
    mfiltered_mf = mf[mf["municipality"].isin(selected_municipality)]

    # HEATMAP
    pivot_df = mfiltered_mf.pivot_table(
        index="municipality", # Rows = municipalities
        columns="year",
        values="palay_production",
        aggfunc="sum" # Sum if multiple entries
    )

    fig = px.imshow(
        pivot_df,
        color_continuous_scale="Greens",
        labels=dict(
            x="Year",
            y="Municipality",
            color="Production (MT)"
        ),
        text_auto=False
    )

    fig.update_layout(
        title=f"Palay Production Heatmap ({title_muni})",
        xaxis_side="top",
        template="plotly_white",
        margin=dict(l=100, r=40, t=120, b=50),  # Spacing around chart
        height=400 + len(pivot_df) * 20
    )

    fig.update_xaxes(tickangle=-45)

    st.plotly_chart(fig,width="stretch")

    #--------------------------------------------
    # DRY AND WET SEASON LINE CHART
    st.markdown(
        "<h3 style='color: #1a3c34; margin-bottom: .3rem; font-size: 22px;'>Seasonal Production Trends</h3>",
        unsafe_allow_html=True
    ) # Subtitle for seasonal trends

    # CREATE COLUMNS
    col1, col2 = st.columns(2, gap="large")

    # -----------------------------
    # FUNCTION TO PLOT SEASON CHART
    # -----------------------------
    #Wet season
    def plot_season_chart(data, season_col, title):
        # GROUP DATA
        seasonal_df = data.groupby(
            ["year", "municipality"]
        )[[season_col]].sum().reset_index() # Sum production for the season

        # LINE CHART
        fig = px.line(
            seasonal_df,
            x="year",
            y=season_col,
            color="municipality" if len(selected_municipality) > 1 else None,
            line_shape="spline",
            markers=True,
            color_discrete_sequence=px.colors.qualitative.Set2  # Use qualitative palette
        )

        # LAYOUT
        fig.update_layout(
            title=title,
            template="plotly_white",
            margin=dict(l=10, r=10, t=60, b=80),
            legend_title="Municipality" if len(selected_municipality) > 1 else None,
            legend=dict(
                orientation="h",
                yanchor="top",
                y=-0.39,
                xanchor="center",
                x=0.5
            ),
            height=450,
            xaxis=dict(
                title="Year",
                tickangle=-45,
                automargin=True
            ),
            yaxis=dict(
                title="Production (MT)",
                automargin=True
            )
        )

        return fig

    # -----------------------------
    # DRY SEASON CHART
    # -----------------------------
    with col1:
        fig_dry = plot_season_chart(
            mfiltered_mf,
            "dry_season",
            f"Dry Season Production ({title_muni})"
        )
        st.plotly_chart(fig_dry, width="stretch")

    # -----------------------------
    # WET SEASON CHART
    # -----------------------------
    with col2:
        fig_wet = plot_season_chart(
            mfiltered_mf,
            "wet_season",
            f"Wet Season Production ({title_muni})"
        )
        st.plotly_chart(fig_wet, width="stretch")


    #Average production per municipality
    # Group data properly
    avg_df = mfiltered_mf.groupby(
        ["year", "municipality"]
    )[["ave_production"]].mean().reset_index()

    # Determine x-axis
    if len(selected_municipality) == 1:
        x_val = "year"
        color_val = None
    else:
        x_val = "year"
        color_val = "municipality" # Multiple colors

    # Plot
    fig_yield = px.line(
        avg_df,
        x=x_val,
        y="ave_production",
        color="municipality" if len(selected_municipality) > 1 else None,
        markers=True,
        color_discrete_sequence=px.colors.qualitative.Set2,
        title=(
            f"Average Production of {selected_municipality[0]}"
            if len(selected_municipality) == 1
            else f"Average Production by {title_muni}"
        ),
        template="plotly_white"
    )

    st.plotly_chart(fig_yield,width="stretch")

    # END OF MUNICIPAL LEVEL
    st.markdown(
        '<hr style="border:1px solid black; margin:0px 0; margin-top: 15px;">',
        unsafe_allow_html=True
    )

    #START OF SUFFICIENCY INFORMATION
    st.markdown(
        "<h2 style='text-align: left; color: black; font-size: 25px; margin-top: 1.3rem; margin-bottom: 1rem;'>Sufficiency Status Report</h2>",
        unsafe_allow_html=True
    )

    # -----------------------------
    # AUTO USE ALL YEARS
    # -----------------------------
    years = sorted(sr["year"].unique())

    # Filter DataFrame
    sr_filtered = sr[sr["year"].isin(years)].copy()

    # Sort
    sr_filtered = sr_filtered.sort_values("year")

    # Sufficiency ratio
    sr_filtered["sufficiency_ratio"] = (
            sr_filtered["net_production_clean_rice"] /
            sr_filtered["actual_consumption"]
    )

    # Year range label
    year_range = f"{min(years)}–{max(years)}"

    # -----------------------------
    # LAYOUT
    # -----------------------------
    col1, col2 = st.columns(2, gap="large")

    # -----------------------------
    # LEFT: Production vs Consumption
    # -----------------------------
    with col1:
        fig_prod_cons = px.bar(
            sr_filtered,
            x="year",
            y=["net_production_clean_rice", "actual_consumption"],
            barmode="group",
            color_discrete_map={
                "net_production_clean_rice": colors[1],
                "actual_consumption": "#C62828"
            },
            title=f"Production vs Consumption ({year_range})",
            template="plotly_white"
        )

        fig_prod_cons.update_layout(
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.40,
                xanchor="right",
                x=0.5
            )
        )

        st.plotly_chart(fig_prod_cons,width="stretch")

    # -----------------------------
    # RIGHT: Sufficiency Ratio
    # -----------------------------
    with col2:
        fig_ratio = px.line(
            sr_filtered,
            x="year",
            y="sufficiency_ratio",
            markers=True,
            color_discrete_sequence=["#4CAF50"],
            title=f"Sufficiency Ratio ({year_range})",
            template="plotly_white"
        )

        fig_ratio.add_hline(
            y=1,
            line_dash="dash",
            line_color="gray",
            annotation_text="Sufficient Level",
            annotation_position="top left"
        )

        st.plotly_chart(fig_ratio,width="stretch")

    # -----------------------------
    # BOTTOM: Surplus / Deficit
    # -----------------------------
    fig_surplus_deficit = px.bar(
        sr_filtered,
        x="year",
        y=sr_filtered["surplusdeficit"].abs(),
        title=f"Surplus / Deficit ({year_range})",
        template="plotly_white"
    )

    fig_surplus_deficit.update_traces(
        marker_color=[
            "#2E7D32" if v >= 0 else "#C62828"
            for v in sr_filtered["surplusdeficit"]
        ]
    )

    st.plotly_chart(fig_surplus_deficit, width="stretch")

    # Footer
    st.markdown("---")
    st.markdown(f"""
        <div style='text-align: center; padding: 1.5rem; 
                    background: linear-gradient(90deg, #E8F5E8 0%, #F1F8E9 100%);
                    border-radius: 15px; color: #2E7D32;'>
            <p style='margin: 0; font-size: 1rem; font-weight: 500;'> Forecast updated: {next_month_name}</p>
        </div>
    """, unsafe_allow_html=True)
