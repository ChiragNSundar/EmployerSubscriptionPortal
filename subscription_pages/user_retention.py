from dash import html, dcc, dash_table, Input, Output
import dash_bootstrap_components as dbc
import plotly.express as px
import pandas as pd
import traceback
from datetime import datetime, timezone

# --- LAYOUT ---
layout = html.Div([
    html.H2("⏳ Subscription Duration Analysis", className="mb-4 text-center text-white"),
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
            # 🧹 CALCULATE DURATION (USER LEVEL)
            # ==============================================================================

            # Filter valid start dates & Deduplicate
            df_dur = df.dropna(subset=['initialSubsStartDate']).copy()
            sort_col = 'timeModifiedDB' if 'timeModifiedDB' in df.columns else 'initialSubsStartDate'
            df_dur = df_dur.sort_values(by=sort_col, ascending=False)
            df_dur = df_dur.drop_duplicates(subset=['User_ID'], keep='first').copy()

            now_utc = pd.Timestamp.now(timezone.utc)

            def calculate_duration(row):
                start = row['initialSubsStartDate']
                end = row['subscriptionCanceledAt']

                if pd.notnull(end):
                    val = (end - start).total_seconds() / 86400
                    status = "Cancelled"
                else:
                    val = (now_utc - start).total_seconds() / 86400
                    status = "Active"
                return pd.Series([val, status])

            df_dur[['Duration_Days', 'Status']] = df_dur.apply(calculate_duration, axis=1)
            # Remove negatives
            df_dur['Duration_Days'] = df_dur['Duration_Days'].fillna(0).clip(lower=0)

            # ==============================================================================
            # 🧮 CALCULATIONS
            # ==============================================================================

            total_users = len(df_dur)

            # --- 1. User Level Buckets ---
            def get_stats(condition):
                count = len(df_dur[condition])
                pct = (count / total_users * 100) if total_users > 0 else 0
                return count, pct

            c1, p1 = get_stats(df_dur['Duration_Days'] <= 10)
            c2, p2 = get_stats((df_dur['Duration_Days'] > 10) & (df_dur['Duration_Days'] <= 30))
            c3, p3 = get_stats((df_dur['Duration_Days'] > 30) & (df_dur['Duration_Days'] <= 60))
            c4, p4 = get_stats((df_dur['Duration_Days'] > 60) & (df_dur['Duration_Days'] <= 365))
            c5, p5 = get_stats(df_dur['Duration_Days'] > 365)

            # --- 2. EMPLOYER & MODE STATS ---
            if not df_dur.empty:
                # A. Employer Stats (Group by Company)
                df_company_agg = df_dur.groupby('User_ID')['Duration_Days'].mean()
                total_companies = len(df_company_agg)

                # Percentiles
                emp_p25_val = df_company_agg.quantile(0.25)
                emp_p75_val = df_company_agg.quantile(0.75)

                # Mean & Median (NEW)
                emp_mean_val = df_company_agg.mean()
                emp_median_val = df_company_agg.median()

                # B. User Modes (Top 3 Occurrences + Count)
                df_user_rounded = df_dur['Duration_Days'].round(0).astype(int)
                top_modes_series = df_user_rounded.value_counts().head(3)

                mode_data = []
                for days, count in top_modes_series.items():
                    mode_data.append(f"{days} Days ({count} Users)")

                while len(mode_data) < 3:
                    mode_data.append("-")

                mode_str_1, mode_str_2, mode_str_3 = mode_data[0], mode_data[1], mode_data[2]

            else:
                total_companies = 0
                emp_p25_val = 0
                emp_p75_val = 0
                emp_mean_val = 0
                emp_median_val = 0
                mode_str_1, mode_str_2, mode_str_3 = "-", "-", "-"

            # ==============================================================================
            # 🖥️ UI COMPONENTS
            # ==============================================================================

            # --- Helper to create uniform cards ---
            def create_bucket_card(title, count, pct, color, desc):
                return dbc.Col(dbc.Card([
                    dbc.CardHeader(title, className=f"text-{color} fw-bold"),
                    dbc.CardBody([
                        html.H3(f"{count}", className=f"text-{color}"),
                        html.H5(f"{pct:.1f}%", className="text-muted"),
                        html.Small(desc, className="text-muted")
                    ])
                ], className=f"text-center shadow-sm h-100 border-{color}", style={"borderTopWidth": "4px"}),
                    width=True)

            # --- Row 1: The 5 Buckets ---
            bucket_cards = dbc.Row([
                create_bucket_card("1-10 Days", c1, p1, "danger", "Immediate Drop-off"),
                create_bucket_card("11-30 Days", c2, p2, "warning", "First Month"),
                create_bucket_card("31-60 Days", c3, p3, "info", "Getting Settled"),
                create_bucket_card("61-365 Days", c4, p4, "primary", "Long Term"),
                create_bucket_card("365+ Days", c5, p5, "success", "Loyal Year+"),
            ], className="mb-4 align-items-stretch")

            # --- Row 2: General Stats ---
            def create_stat_card(title, value, suffix="Days", color="dark"):
                return dbc.Col(dbc.Card([
                    dbc.CardBody([
                        html.H6(title, className="text-muted"),
                        html.H3(f"{value}", className=f"text-{color}"),
                        html.Small(suffix, className="text-muted") if suffix else None
                    ])
                ], className="text-center shadow-sm h-100"), width=True)

            general_stats = dbc.Row([
                # 1. Total Counts
                dbc.Col(dbc.Card([
                    dbc.CardBody([
                        html.H6("Total Analyzed", className="text-muted"),
                        html.Div([
                            html.Span(f"{total_users} Users", className="fw-bold me-2"),
                        ])
                    ])
                ], className="text-center shadow-sm h-100"), width=2),

                # 2. Employer Mean (NEW)
                create_stat_card("Employer Mean", f"{emp_mean_val:.1f}", suffix="Avg Days", color="info"),

                # 3. Employer Median (NEW)
                create_stat_card("Employer Median", f"{emp_median_val:.1f}", suffix="Avg Days", color="primary"),

                # 4. Employer 25th Percentile
                create_stat_card("Employer 25th %", f"{emp_p25_val:.1f}", suffix="Avg Days", color="warning"),

                # 5. Employer 75th Percentile
                create_stat_card("Employer 75th %", f"{emp_p75_val:.1f}", suffix="Avg Days", color="success"),

                # 6. User Modes (Top 3)
                dbc.Col(dbc.Card([
                    dbc.CardBody([
                        html.H6("User Modes (Top 3)", className="text-muted"),
                        html.Div([
                            html.Span("1️⃣ " + str(mode_str_1), className="d-block fw-bold text-dark"),
                            html.Span("2️⃣ " + str(mode_str_2), className="d-block text-secondary"),
                            html.Span("3️⃣ " + str(mode_str_3), className="d-block text-muted small"),
                        ])
                    ])
                ], className="text-center shadow-sm h-100"), width=True),

            ], className="mb-4 align-items-stretch")

            # --- Graph ---
            fig_hist = px.histogram(
                df_dur,
                x='Duration_Days',
                color='Status',
                nbins=50,
                title="📊 User Duration Distribution (with Employer Percentiles)",
                labels={'Duration_Days': 'Days Subscribed'},
                color_discrete_map={'Active': '#2ecc71', 'Cancelled': '#e74c3c'}
            )

            # Add lines for Employer Percentiles
            # fig_hist.add_vline(x=emp_p25_val, line_dash="dash", line_color="orange", annotation_text="Emp 25%")
            # fig_hist.add_vline(x=emp_median_val, line_dash="dash", line_color="blue", annotation_text="Emp Median")
            # fig_hist.add_vline(x=emp_p75_val, line_dash="dash", line_color="green", annotation_text="Emp 75%")

            fig_hist.update_layout(template="plotly_white", bargap=0.1)

            # --- Table ---
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

            # --- RETURN ---
            return html.Div([
                html.H4("📅 Retention Buckets (User Count & %)", className="text-white mb-3"),
                bucket_cards,

                html.H4("🧮 Statistics (Employer & User)", className="text-white mb-3"),
                general_stats,

                dbc.Row([
                    dbc.Col(dbc.Card(dbc.CardBody(dcc.Graph(figure=fig_hist)), className="shadow-sm mb-4"), width=12)
                ]),

                html.H4("📋 Top 50 Longest Durations", className="text-white mb-2"),
                table_section
            ])

        except Exception as e:
            return dbc.Alert([html.H4("Error processing data"), html.Pre(traceback.format_exc())], color="danger")