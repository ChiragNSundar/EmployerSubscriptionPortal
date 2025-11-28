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
    html.H3("Monthly Paid Subscriptions & Revenue", className="my-4 text-center"),

    # --- Row 0: Filters ---
    dbc.Row([
        # 1. Month Filter (Replaced Date Range Picker)
        dbc.Col([
            html.Label("Select Month(s):", className="control-label"),
            dcc.Dropdown(
                id='paid-month-dropdown',
                options=[],
                multi=True,
                placeholder="Select Months...",
                className="mb-3"
            )
        ], width=12, md=4),

        # 2. Country Filter
        dbc.Col([
            html.Label("Select Country:", className="control-label"),
            dcc.Dropdown(
                id='paid-monthly-country-dropdown',
                options=[],
                multi=True,
                placeholder="All Countries",
                className="mb-3"
            )
        ], width=12, md=4),

        # 3. Type Filter
        dbc.Col([
            html.Label("Select Subscription Type:", className="control-label"),
            dcc.Dropdown(
                id='paid-monthly-type-dropdown',
                options=[],
                multi=True,
                placeholder="All Paid Types",
                className="mb-3"
            )
        ], width=12, md=4),

    ], className="mb-4 glass-container"),

    # --- Row 1: Placards (5 Cards) ---
    dbc.Row([
        dbc.Col(create_card("Total Paid Subs", "card-monthly-paid-total", color="dark"), width=12, md=4, lg=2),
        dbc.Col(create_card("Total Revenue EUR(€)", "card-monthly-paid-revenue", color="success"), width=12, md=4, lg=3),
        dbc.Col(create_card("New Total", "card-monthly-paid-new", color="primary"), width=6, md=4, lg=2),
        dbc.Col(create_card("Renewed Total", "card-monthly-paid-renewed", color="info"), width=6, md=4, lg=2),
        dbc.Col(create_card("Upgraded Total", "card-monthly-paid-upgraded", color="warning"), width=6, md=4, lg=2),
    ], className="mb-2 justify-content-center"),

    # --- Row 2: Bar Graph ---
    dbc.Row([
        dbc.Col([
            dbc.Card([
                #dbc.CardHeader("Monthly Paid Subscriptions Trend"),
                dbc.CardBody([
                    dcc.Graph(id='paid-monthly-bar-graph', style={'height': '500px'})
                ])
            ], className="shadow-sm glass-container")
        ], width=12)
    ])
], fluid=True)


# --- 2. CALLBACK REGISTRATION ---
def register_callbacks(app):
    # --- Callback A: Populate Dropdown Options (Months, Country, Type) ---
    @app.callback(
        [Output('paid-month-dropdown', 'options'),
         Output('paid-monthly-country-dropdown', 'options'),
         Output('paid-monthly-type-dropdown', 'options')],
        Input('global-data-store', 'data')
    )
    def update_paid_monthly_filter_options(data):
        if not data:
            return [], [], []

        df = pd.DataFrame(data)

        # 1. Month Options (NEW)
        month_opts = []
        if 'Date' in df.columns:
            # Convert to datetime
            temp_dates = pd.to_datetime(df['Date'], errors='coerce').dropna()
            # Extract Year-Month (e.g., "2023-01")
            # We create a dataframe to sort easily
            dates_df = pd.DataFrame({'date': temp_dates})
            dates_df['label'] = dates_df['date'].dt.strftime('%b %Y')  # Jan 2023
            dates_df['value'] = dates_df['date'].dt.strftime('%Y-%m')  # 2023-01

            # Get unique values and sort descending (newest first)
            unique_months = dates_df[['label', 'value']].drop_duplicates().sort_values('value', ascending=False)

            month_opts = unique_months.to_dict('records')

        # 2. Country Options
        country_opts = []
        if 'Location' in df.columns:
            countries = sorted(df['Location'].dropna().unique().astype(str))
            country_opts = [{'label': c, 'value': c} for c in countries]

        # 3. Type Options (Only Paid Types)
        type_opts = []
        if 'Subscription_Type' in df.columns:
            all_types = df['Subscription_Type'].dropna().unique()
            valid_paid_labels = ['New', 'Renewed', 'Upgraded']
            filtered_types = [t for t in all_types if str(t).title() in valid_paid_labels]
            type_opts = [{'label': str(t).title(), 'value': t} for t in sorted(filtered_types)]

        return month_opts, country_opts, type_opts

    # --- Callback B: Update Dashboard ---
    @app.callback(
        [
            Output('card-monthly-paid-total', 'children'),
            Output('card-monthly-paid-revenue', 'children'),
            Output('card-monthly-paid-new', 'children'),
            Output('card-monthly-paid-renewed', 'children'),
            Output('card-monthly-paid-upgraded', 'children'),
            Output('paid-monthly-bar-graph', 'figure')
        ],
        [
            Input('global-data-store', 'data'),
            Input('paid-month-dropdown', 'value'),  # Changed from start/end date
            Input('paid-monthly-country-dropdown', 'value'),
            Input('paid-monthly-type-dropdown', 'value')
        ]
    )
    def update_paid_monthly_overview(data, selected_months, selected_countries, selected_types):
        # 1. Handle Empty Data
        if not data:
            return "0", "€ 0", "0", "0", "0", px.bar(title="No Data Available")

        df = pd.DataFrame(data)

        # 2. Data Pre-processing
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')

        if 'lastPaymentReceivedOn' in df.columns:
            df['lastPaymentReceivedOn'] = pd.to_datetime(df['lastPaymentReceivedOn'], errors='coerce')
        else:
            return "0", "€ 0", "0", "0", "0", px.bar(title="Missing Payment Data Column")

        if 'lastAmountPaidEUR' in df.columns:
            df['lastAmountPaidEUR'] = pd.to_numeric(df['lastAmountPaidEUR'], errors='coerce').fillna(0)
        else:
            df['lastAmountPaidEUR'] = 0

        if 'Subscription_Type' in df.columns:
            df['type_norm'] = df['Subscription_Type'].astype(str).str.lower()
        else:
            df['type_norm'] = "unknown"

        # --- 3. APPLY "PAID" LOGIC & TYPE FILTER ---
        base_paid_types = ['new', 'renewed', 'upgraded']

        if selected_types:
            selected_types_lower = [t.lower() for t in selected_types]
            target_types = [t for t in selected_types_lower if t in base_paid_types]
        else:
            target_types = base_paid_types

        # Masks
        type_mask = df['type_norm'].isin(target_types)
        payment_mask = (df['lastPaymentReceivedOn'] >= df['Date']).fillna(False)

        df_paid = df[type_mask & payment_mask].copy()

        # --- 4. APPLY REMAINING FILTERS ---

        # A. Month Filter (NEW)
        if selected_months:
            # Create a temporary column formatted as 'YYYY-MM' to match the dropdown values
            df_paid['month_str'] = df_paid['Date'].dt.strftime('%Y-%m')
            df_paid = df_paid[df_paid['month_str'].isin(selected_months)]

        # B. Country Filter
        if selected_countries:
            if 'Location' in df_paid.columns:
                df_paid = df_paid[df_paid['Location'].isin(selected_countries)]

        # --- 5. CALCULATE PLACARDS ---
        total_paid_count = len(df_paid)
        total_revenue = df_paid['lastAmountPaidEUR'].sum()

        counts = df_paid['type_norm'].value_counts()
        count_new = counts.get('new', 0)
        count_renewed = counts.get('renewed', 0)
        count_upgraded = counts.get('upgraded', 0)

        # --- 6. GENERATE MONTHLY GRAPH ---

        if df_paid.empty:
            fig = px.bar(title="No Paid Subscriptions Found for Selected Filters")
        else:
            # Create a Month-Year column (First day of the month) for grouping
            df_paid['month_start'] = df_paid['Date'].dt.to_period('M').dt.to_timestamp()

            # Group by Month
            df_grouped = df_paid.groupby('month_start').size().reset_index(name='count')
            df_grouped = df_grouped.sort_values('month_start')

            # Create Plot
            fig = px.bar(
                df_grouped,
                x='month_start',
                y='count',
                title="Monthly Paid Subscriptions",
                labels={'month_start': 'Month', 'count': 'Count of Paid Subs'},
                template="plotly_white",
                color_discrete_sequence=['#198754']  # Success Green
            )

            # Force X-Axis to show MONTHS (e.g., Jan 2023)
            fig.update_xaxes(
                dtick="M1",  # Tick every 1 month
                tickformat="%b %Y",  # Format: Jan 2023
                title_text="Month"
            )

            fig.update_layout(hovermode="x unified")

        revenue_str = f"€ {total_revenue:,.2f}"

        return (
            f"{total_paid_count:,}",
            revenue_str,
            f"{count_new:,}",
            f"{count_renewed:,}",
            f"{count_upgraded:,}",
            fig
        )

"""
SQL QUERY FOR THE LOGIC:

SELECT 
    COUNT(*) AS total_paid_subscriptions,
    SUM(lastAmountPaidEUR) AS total_revenue
FROM 
    graph_subscription
WHERE 
    type IN ('New', 'Renewed', 'Upgraded') 
    AND lastPaymentReceivedOn >= dateUTC;

"""