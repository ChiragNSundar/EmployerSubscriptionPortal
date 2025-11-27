import pandas as pd
import plotly.express as px
from dash import html, dcc, Input, Output, callback
import dash_bootstrap_components as dbc


# --- 1. LAYOUT DEFINITION ---
def create_card(title, card_id, color="primary"):
    """Helper function to create a styled summary card."""
    return dbc.Card(
        dbc.CardBody([
            html.H5(title, className="card-title", style={'fontSize': '1rem', 'opacity': '0.8'}),
            html.H2("0", id=card_id, className="card-text", style={'fontWeight': 'bold'})
        ]),
        color=color,
        inverse=True,
        className="mb-4 shadow-sm"
    )


layout = dbc.Container([
    html.H3("Monthly Trend Dashboard", className="my-4 text-center"),

    # --- Row 0: Filters ---
    dbc.Row([
        # 1. Month Filter (Replaces Date Range)
        dbc.Col([
            html.Label("Select Month(s):", className="fw-bold"),
            dcc.Dropdown(
                id='month-dropdown',
                options=[],  # Populated via callback
                multi=True,
                placeholder="All Months",
                className="mb-3"
            )
        ], width=12, md=4),

        # 2. Country Filter
        dbc.Col([
            html.Label("Select Country:", className="fw-bold"),
            dcc.Dropdown(
                id='country-dropdown-monthly',  # Unique ID for this page
                options=[],
                multi=True,
                placeholder="All Countries",
                className="mb-3"
            )
        ], width=12, md=4),

        # 3. Type Filter
        dbc.Col([
            html.Label("Select Subscription Type:", className="fw-bold"),
            dcc.Dropdown(
                id='type-dropdown-monthly',  # Unique ID for this page
                options=[],
                multi=True,
                placeholder="All Types",
                className="mb-3"
            )
        ], width=12, md=4),

    ], className="mb-4 p-3 bg-light rounded shadow-sm"),

    # --- Row 1: Placards ---
    dbc.Row([
        dbc.Col(create_card("Total Records", "card-total-m", color="dark"), width=12, md=4, lg=2),
        dbc.Col(create_card("New", "card-new-m", color="success"), width=6, md=4, lg=2),
        dbc.Col(create_card("Trial", "card-trial-m", color="info"), width=6, md=4, lg=2),
        dbc.Col(create_card("Renewed", "card-renewed-m", color="primary"), width=6, md=4, lg=2),
        dbc.Col(create_card("Upgraded", "card-upgraded-m", color="warning"), width=6, md=4, lg=2),
        dbc.Col(create_card("Cancelled", "card-cancelled-m", color="danger"), width=6, md=4, lg=2),
    ], className="mb-2"),

    # --- Row 2: Bar Graph ---
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Monthly Trend by Subscription Type"),
                dbc.CardBody([
                    dcc.Graph(id='monthly-type-bar-graph', style={'height': '500px'})
                ])
            ], className="shadow-sm")
        ], width=12)
    ])
], fluid=True)


# --- 2. CALLBACK REGISTRATION ---
def register_callbacks(app):
    # --- Callback A: Populate Dropdown Options ---
    @app.callback(
        [Output('month-dropdown', 'options'),
         Output('country-dropdown-monthly', 'options'),
         Output('type-dropdown-monthly', 'options')],
        Input('global-data-store', 'data')
    )
    def update_filter_options(data):
        if not data:
            return [], [], []

        df = pd.DataFrame(data)

        # 1. Month Options (Format: "January 2023", Value: "2023-01")
        month_opts = []
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
            # Extract Year-Month for sorting and display
            df['Month_Val'] = df['Date'].dt.to_period('M').astype(str)  # 2023-01

            # Get unique months and sort them
            unique_months = sorted(df['Month_Val'].dropna().unique())

            # Create options
            month_opts = [
                {'label': pd.to_datetime(m).strftime('%B %Y'), 'value': m}
                for m in unique_months
            ]

        # 2. Country Options
        country_opts = []
        if 'Location' in df.columns:
            countries = sorted(df['Location'].dropna().unique().astype(str))
            country_opts = [{'label': c, 'value': c} for c in countries]

        # 3. Type Options
        type_opts = []
        if 'Subscription_Type' in df.columns:
            types = sorted(df['Subscription_Type'].dropna().astype(str).unique())
            type_opts = [{'label': t.title(), 'value': t} for t in types]

        return month_opts, country_opts, type_opts

    # --- Callback B: Update Dashboard ---
    @app.callback(
        [
            Output('card-total-m', 'children'),
            Output('card-new-m', 'children'),
            Output('card-trial-m', 'children'),
            Output('card-renewed-m', 'children'),
            Output('card-upgraded-m', 'children'),
            Output('card-cancelled-m', 'children'),
            Output('monthly-type-bar-graph', 'figure')
        ],
        [
            Input('global-data-store', 'data'),
            Input('month-dropdown', 'value'),
            Input('country-dropdown-monthly', 'value'),
            Input('type-dropdown-monthly', 'value')
        ]
    )
    def update_monthly_overview(data, selected_months, selected_countries, selected_types):
        # 1. Handle Empty Data
        if not data:
            empty_fig = px.bar(title="No Data Available")
            return "0", "0", "0", "0", "0", "0", empty_fig

        df = pd.DataFrame(data)

        # 2. Pre-process Date & Month
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
            # Create a 'Month_Start' date (always 1st of month) for plotting
            df['Month_Start'] = df['Date'].dt.to_period('M').dt.to_timestamp()
            # Create string version for filtering
            df['Month_Str'] = df['Date'].dt.to_period('M').astype(str)
        else:
            df['Month_Start'] = None
            df['Month_Str'] = "Unknown"

        # 3. Pre-process Type
        if 'Subscription_Type' in df.columns:
            df['type_norm'] = df['Subscription_Type'].astype(str).str.lower()
        else:
            df['type_norm'] = "unknown"
            df['Subscription_Type'] = "Unknown"

        # --- 4. APPLY FILTERS ---

        # A. Month Filter
        if selected_months:
            df = df[df['Month_Str'].isin(selected_months)]

        # B. Country Filter
        if selected_countries:
            if 'Location' in df.columns:
                df = df[df['Location'].isin(selected_countries)]

        # C. Type Filter
        if selected_types:
            df = df[df['Subscription_Type'].isin(selected_types)]

        # --- 5. CALCULATE PLACARDS ---
        total_count = len(df)
        counts = df['type_norm'].value_counts()

        count_new = counts.get('new', 0)
        count_trial = counts.get('trial', 0)
        count_renewed = counts.get('renewed', 0)
        count_upgraded = counts.get('upgraded', 0)
        count_cancelled = counts.get('cancelled', 0)

        # --- 6. GENERATE GRAPH ---

        if df.empty:
            fig = px.bar(title="No Data Found for Selected Filters")
        else:
            # A. Group Data by Month Start
            df_grouped = df.groupby(['Month_Start', 'Subscription_Type']).size().reset_index(name='count')

            # B. Fix "Skipped Months" (Fill Gaps)
            # Find min/max month in the filtered data (or based on selection if we wanted to be strict)
            if not df_grouped.empty:
                min_m = df_grouped['Month_Start'].min()
                max_m = df_grouped['Month_Start'].max()

                # Generate all months between min and max
                full_month_range = pd.date_range(start=min_m, end=max_m, freq='MS')  # MS = Month Start

                unique_types = selected_types if selected_types else df['Subscription_Type'].unique()

                # Create MultiIndex (All Months x All Types)
                multi_idx = pd.MultiIndex.from_product([full_month_range, unique_types],
                                                       names=['Month_Start', 'Subscription_Type'])

                # Reindex
                df_grouped = df_grouped.set_index(['Month_Start', 'Subscription_Type']).reindex(multi_idx,
                                                                                                fill_value=0).reset_index()

            # C. Create Plot
            fig = px.bar(
                df_grouped,
                x='Month_Start',
                y='count',
                color='Subscription_Type',
                barmode='group',
                title="Monthly Subscriptions by Type",
                labels={'Month_Start': 'Month', 'count': 'Total Subscriptions', 'Subscription_Type': 'Status'},
                template="plotly_white",
                color_discrete_map={
                    'new': '#198754', 'New': '#198754',
                    'trial': '#0dcaf0', 'Trial': '#0dcaf0',
                    'renewed': '#0d6efd', 'Renewed': '#0d6efd',
                    'upgraded': '#ffc107', 'Upgraded': '#ffc107',
                    'cancelled': '#dc3545', 'Cancelled': '#dc3545'
                }
            )

            # D. Force X-Axis to show Month Names
            fig.update_xaxes(
                dtick="M1",  # Tick every 1 month
                tickformat="%b",  # <--- SHOWS MONTH NAME (e.g., Jan, Feb)
                title_text="Month"
            )

            fig.update_layout(
                yaxis_title="Count",
                legend_title="Subscription Type",
                hovermode="x unified"
            )

        return (
            f"{total_count:,}",
            f"{count_new:,}",
            f"{count_trial:,}",
            f"{count_renewed:,}",
            f"{count_upgraded:,}",
            f"{count_cancelled:,}",
            fig
        )