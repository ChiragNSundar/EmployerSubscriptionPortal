from dash import html, dcc, dash_table, Input, Output
import dash_bootstrap_components as dbc
import plotly.express as px
import pandas as pd
import numpy as np
import traceback
from datetime import datetime, timezone

# --- LAYOUT ---
layout = html.Div([
    html.H2("⏳ Subscription Duration & Cohort Analysis", className="mb-4 text-center text-white"),
    html.Div(id="duration-buckets-content")
])


# --- LOGIC & CALLBACKS ---
def register_callbacks(app):
    @app.callback(
        Output("duration-buckets-content", "children"),
        Input("global-data-store", "data")
    )
    def update_duration_buckets(data):
        if not data:
            return dbc.Alert("Global Data Store is empty.", color="warning")

        try:
            # 1. Load Data
            df = pd.DataFrame(data)

            # 2. Check Columns
            required_cols = ['initialSubsStartDate', 'User_ID', 'Company']
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                return dbc.Alert(f"Data missing required columns: {missing_cols}", color="danger")

            # 3. Date Conversion
            df['initialSubsStartDate'] = pd.to_datetime(df['initialSubsStartDate'], errors='coerce', utc=True)
            if 'subscriptionCanceledAt' in df.columns:
                df['subscriptionCanceledAt'] = pd.to_datetime(df['subscriptionCanceledAt'], errors='coerce', utc=True)
            else:
                df['subscriptionCanceledAt'] = pd.NaT

            # ==============================================================================
            # PART A: DURATION ANALYSIS
            # ==============================================================================

            # 1. Filter valid start dates
            df_dur = df.dropna(subset=['initialSubsStartDate']).copy()

            # 2. Sort to ensure we have the latest record
            sort_col = 'Date' if 'Date' in df.columns else 'initialSubsStartDate'
            df_dur = df_dur.sort_values(by=sort_col, ascending=False)

            # 3. Deduplicate: Get UNIQUE Users
            df_dur = df_dur.drop_duplicates(subset=['User_ID'], keep='first').copy()

            now_utc = pd.Timestamp.now(timezone.utc)

            # --- DURATION LOGIC ---
            def calculate_duration(row):
                start = row['initialSubsStartDate']
                end = row['subscriptionCanceledAt']

                # Logic: If Cancel Date is NULL -> Active, Else -> Cancelled
                if pd.isnull(end):
                    status = "Active"
                    # Active Duration = Today - Start Date (Used for Funnel/Buckets only)
                    val = (now_utc - start).total_seconds() / 86400
                else:
                    status = "Cancelled"
                    # Cancelled Duration = Cancel Date - Start Date (Used for Stats)
                    val = (end - start).total_seconds() / 86400

                return pd.Series([val, status])

            df_dur[['Duration_Days', 'Status']] = df_dur.apply(calculate_duration, axis=1)

            # Clean up negatives
            df_dur['Duration_Days'] = df_dur['Duration_Days'].fillna(0).clip(lower=0)

            # 🧮 CALCULATIONS (Survival / Funnel) - USES ALL USERS
            total_unique_users = len(df_dur)

            # --- Function to calculate Cumulative Survival ---
            def get_survival_stats(days_threshold):
                survivors_df = df_dur[df_dur['Duration_Days'] > days_threshold]
                count = len(survivors_df)
                if total_unique_users > 0:
                    pct_of_total = (count / total_unique_users) * 100
                else:
                    pct_of_total = 0.0
                return count, pct_of_total

            # Apply logic (Cumulative Thresholds)
            c1, p1 = get_survival_stats(0)  # 1-10 Days
            c2, p2 = get_survival_stats(10)  # 11-30 Days
            c3, p3 = get_survival_stats(30)  # 31-60 Days
            c4, p4 = get_survival_stats(60)  # 61-365 Days
            c5, p5 = get_survival_stats(365)  # 365+ Days

            # PART A.2: STATISTICS (CANCELLED USERS ONLY)

            # 1. Create a subset of ONLY Cancelled users
            # We ignore 'Active' users for Mean, Median, Mode, etc.
            df_cancelled_only = df_dur[df_dur['Status'] == 'Cancelled'].copy()

            total_cancelled_users = len(df_cancelled_only)

            if not df_cancelled_only.empty:
                # We calculate stats on the duration of people who actually left
                stats_series = df_cancelled_only['Duration_Days']

                emp_mean_val = stats_series.mean()
                emp_median_val = stats_series.median()
                emp_p25_val = stats_series.quantile(0.25)
                emp_p75_val = stats_series.quantile(0.75)

                # Mode (Top 3 for Cancelled Users)
                df_user_rounded = stats_series.round(0).astype(int)
                top_modes_series = df_user_rounded.value_counts().head(3)
                mode_data = []
                for days, count in top_modes_series.items():
                    mode_data.append(f"{days} Days ({count} Users)")
                while len(mode_data) < 3:
                    mode_data.append("-")
                mode_str_1, mode_str_2, mode_str_3 = mode_data[0], mode_data[1], mode_data[2]
            else:
                emp_p25_val = emp_p75_val = emp_mean_val = emp_median_val = 0
                mode_str_1, mode_str_2, mode_str_3 = "-", "-", "-"

            # PART B: COHORT ANALYSIS (RETENTION HEATMAP)

            # 1. Prepare Data
            df_cohort = df_dur.copy()

            # Calculate Counts for Title
            active_count = df_cohort['subscriptionCanceledAt'].isnull().sum()
            inactive_count = df_cohort['subscriptionCanceledAt'].notnull().sum()

            # 2. Create Cohort Vintage (YYYY-MM)
            df_cohort['CohortVintage'] = df_cohort['initialSubsStartDate'].dt.to_period('M').astype(str)

            # 3. Calculate MonthOnBook
            mask_cancelled = df_cohort['subscriptionCanceledAt'].notnull()
            df_cohort.loc[mask_cancelled, 'MonthOnBook'] = (
                    (df_cohort.loc[mask_cancelled, 'subscriptionCanceledAt'].dt.year - df_cohort.loc[
                        mask_cancelled, 'initialSubsStartDate'].dt.year) * 12 +
                    (df_cohort.loc[mask_cancelled, 'subscriptionCanceledAt'].dt.month - df_cohort.loc[
                        mask_cancelled, 'initialSubsStartDate'].dt.month)
            )

            # 4. Generate Table
            cohort_sizes = df_cohort.groupby('CohortVintage')['User_ID'].nunique().rename('TotalCohortSize')

            cancelled_df = df_cohort.dropna(subset=['MonthOnBook'])
            monthly_cancellations = cancelled_df.groupby(['CohortVintage', 'MonthOnBook'])['User_ID'].count().rename(
                'MonthlyCancellations')

            cohort_table = monthly_cancellations.reset_index()
            cohort_table = cohort_table.merge(cohort_sizes, on='CohortVintage', how='left')

            cohort_table = cohort_table.sort_values(['CohortVintage', 'MonthOnBook'])

            # --- RETENTION CALCULATION ---
            cohort_table['CumulativeCancellations'] = cohort_table.groupby('CohortVintage')[
                'MonthlyCancellations'].cumsum()

            # Calculate Retention Rate: 100 - Cancellation Rate
            cohort_table['RetentionRate'] = 100 - (
                    (cohort_table['CumulativeCancellations'] / cohort_table['TotalCohortSize']) * 100
            )

            # 5. Pivot for Heatmap
            if not cohort_table.empty:
                heatmap_data = cohort_table.pivot_table(
                    index='CohortVintage',
                    columns='MonthOnBook',
                    values='RetentionRate'
                )

                # Forward Fill & Fillna
                heatmap_data = heatmap_data.ffill(axis=1).fillna(100)

                # A. Sort Index: Oldest at Top
                heatmap_data = heatmap_data.sort_index(ascending=True)

                # B. Prepare Axes
                x_values = heatmap_data.columns.astype(int)
                y_labels = heatmap_data.index.astype(str).tolist()

                # Create Plotly Heatmap
                fig_cohort = px.imshow(
                    heatmap_data,
                    x=x_values,
                    y=y_labels,
                    labels=dict(x="Months Since Joining (Month on Book)", y="Cohort Vintage", color="Retention %"),
                    text_auto='.1f',
                    aspect="auto",
                    color_continuous_scale='RdYlGn',
                    zmin=0,
                    zmax=100
                )

                # C. Styling
                fig_cohort.update_traces(xgap=1, ygap=1)

                fig_cohort.update_layout(
                    title=f"User Retention Rate (Active: {active_count} | Inactive: {inactive_count})",
                    title_font_size=16,
                    template="plotly_white",
                    height=800,
                    xaxis={
                        'side': 'bottom',
                        'tickmode': 'linear',
                        'dtick': 2,
                        'tick0': 0
                    },
                    yaxis={'side': 'left'}
                )
            else:
                fig_cohort = px.bar(title="No data available for Cohort Analysis")

            # PART C: UI COMPONENTS

            # --- Helper to create uniform cards ---
            def create_bucket_card(title, count, pct, color, desc):
                return dbc.Col(dbc.Card([
                    dbc.CardHeader(title, className=f"text-{color} fw-bold"),
                    dbc.CardBody([
                        html.H3(f"{count}", className=f"text-{color}"),
                        html.Small("Users Reached", className="text-muted d-block mb-1"),
                        html.H5(f"{pct:.1f}% of Total", className="text-muted"),
                        html.Small(desc, className="text-muted")
                    ])
                ], className=f"text-center shadow-sm h-100 border-{color}", style={"borderTopWidth": "4px"}),
                    width=True)

            # --- Row 1: The 5 Buckets (FUNNEL VIEW) ---
            bucket_cards = dbc.Row([
                create_bucket_card("1-10 Days", c1, p1, "danger", "Started Journey"),
                create_bucket_card("11-30 Days", c2, p2, "warning", "Passed 10 Days"),
                create_bucket_card("31-60 Days", c3, p3, "info", "Passed 1 Month"),
                create_bucket_card("61-365 Days", c4, p4, "primary", "Passed 2 Months"),
                create_bucket_card("365+ Days", c5, p5, "success", "Passed 1 Year"),
            ], className="mb-4 align-items-stretch")

            # --- Row 2: General Stats (UPDATED FOR CANCELLED ONLY) ---
            def create_stat_card(title, value, suffix="Days", color="dark"):
                return dbc.Col(dbc.Card([
                    dbc.CardBody([
                        html.H6(title, className="text-muted"),
                        html.H3(f"{value}", className=f"text-{color}"),
                        html.Small(suffix, className="text-muted") if suffix else None
                    ])
                ], className="text-center shadow-sm h-100"), width=True)

            general_stats = dbc.Row([
                dbc.Col(dbc.Card([
                    dbc.CardBody([
                        html.H6("Total Cancelled", className="text-muted"),
                        html.Div([
                            html.Span(f"{total_cancelled_users} Users", className="fw-bold me-2"),
                        ])
                    ])
                ], className="text-center shadow-sm h-100"), width=2),

                create_stat_card("Cancelled Mean", f"{emp_mean_val:.1f}", suffix="Avg Days", color="info"),
                create_stat_card("Cancelled Median", f"{emp_median_val:.1f}", suffix="Avg Days", color="primary"),
                create_stat_card("Cancelled 25th %", f"{emp_p25_val:.1f}", suffix="Avg Days", color="warning"),
                create_stat_card("Cancelled 75th %", f"{emp_p75_val:.1f}", suffix="Avg Days", color="success"),

                dbc.Col(dbc.Card([
                    dbc.CardBody([
                        html.H6("Cancelled Modes (Top 3)", className="text-muted"),
                        html.Div([
                            html.Span("1️⃣ " + str(mode_str_1), className="d-block fw-bold text-dark"),
                            html.Span("2️⃣ " + str(mode_str_2), className="d-block text-secondary"),
                            html.Span("3️⃣ " + str(mode_str_3), className="d-block text-muted small"),
                        ])
                    ])
                ], className="text-center shadow-sm h-100"), width=True),

            ], className="mb-4 align-items-stretch")

            # --- Graph: Duration Histogram ---
            fig_hist = px.histogram(
                df_dur,
                x='Duration_Days',
                color='Status',
                nbins=50,
                title="📊 User Duration Distribution",
                labels={'Duration_Days': 'Days Subscribed'},
                color_discrete_map={'Active': '#2ecc71', 'Cancelled': '#e74c3c'}
            )
            fig_hist.update_layout(template="plotly_white", bargap=0.1)

            # --- Table: Top 50 ---
            table_data = df_dur[[
                'User_ID', 'Company', 'initialSubsStartDate', 'Status', 'Duration_Days'
            ]].sort_values(by='Duration_Days', ascending=False).head(50)

            table_section = dash_table.DataTable(
                data=table_data.to_dict('records'),
                columns=[
                    {"name": "User ID", "id": "User_ID"},
                    {"name": "Company", "id": "Company"},
                    {"name": "Start Date", "id": "initialSubsStartDate", "type": "datetime"},
                    {"name": "Status", "id": "Status"},
                    {"name": "Duration", "id": "Duration_Days", "type": "numeric", "format": {"specifier": ".1f"}},
                ],
                style_cell={'padding': '10px', 'textAlign': 'left'},
                style_header={'backgroundColor': '#2d3436', 'color': 'white', 'fontWeight': 'bold'},
                style_data_conditional=[
                    {'if': {'filter_query': '{Status} eq "Active"'}, 'color': 'green', 'fontWeight': 'bold'},
                    {'if': {'filter_query': '{Status} eq "Cancelled"'}, 'color': 'red'}
                ],
                page_size=10
            )

            # --- RETURN FINAL LAYOUT ---
            return html.Div([
                html.H4("📅 Survival Funnel (Users Reached & % of Total)", className="text-white mb-3"),
                bucket_cards,

                html.H4("🧮 Statistics (Cancelled Users Only)", className="text-white mb-3"),
                general_stats,

                # 1. Duration Histogram
                dbc.Row([
                    dbc.Col(dbc.Card(dbc.CardBody(dcc.Graph(figure=fig_hist)), className="shadow-sm mb-4"), width=12)
                ]),

                # 2. COHORT HEATMAP (RETENTION)
                dbc.Row([
                    dbc.Col(dbc.Card(dbc.CardBody(dcc.Graph(figure=fig_cohort)), className="shadow-sm mb-4"), width=12)
                ]),

                # 3. Top 50 Table
                html.H4("📋 Top 50 Longest Durations", className="text-white mb-2"),
                table_section
            ])

        except Exception as e:
            return dbc.Alert([html.H4("Error processing data"), html.Pre(traceback.format_exc())], color="danger")