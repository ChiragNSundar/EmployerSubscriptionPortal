import pandas as pd
import plotly.express as px
from dash import html, dcc, Input, Output, callback
import dash_bootstrap_components as dbc


# --- 1. LAYOUT DEFINITION ---
def create_card(title, card_id, color="primary", is_currency=False):
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
    html.H3("Paid Subscriptions & Revenue", className="my-4 text-center"),

    # --- Row 0: Filters ---
    dbc.Row([
        # 1. Date Range Picker
        dbc.Col([
            html.Label("Select Date Range:", className="control-label"),
            html.Div(
                dcc.DatePickerRange(
                    id='paid-date-picker',
                    display_format='YYYY-MM-DD',
                    start_date=None,
                    end_date=None,
                    clearable=True,
                    style={'width': '100%'}
                ),
                className="mb-3"
            )
        ], width=12, md=4),

        # 2. Country Filter
        dbc.Col([
            html.Label("Select Country:", className="control-label"),
            dcc.Dropdown(
                id='paid-country-dropdown',
                options=[],
                multi=True,
                placeholder="All Countries",
                className="mb-3"
            )
        ], width=12, md=4),

        # 3. Type Filter (NEW)
        dbc.Col([
            html.Label("Select Subscription Type:", className="control-label"),
            dcc.Dropdown(
                id='paid-type-dropdown',
                options=[],
                multi=True,
                placeholder="All Paid Types",
                className="mb-3"
            )
        ], width=12, md=4),

    ], className="mb-4  glass-container"),

    # --- Row 1: Placards (5 Cards) ---
    dbc.Row([
        dbc.Col(create_card("Total Paid Subs", "card-paid-total", color="dark"), width=12, md=4, lg=2),
        dbc.Col(create_card("Total Revenue EUR(€) ", "card-paid-revenue", color="success"), width=12, md=4, lg=3),
        dbc.Col(create_card("New Total", "card-paid-new", color="primary"), width=6, md=4, lg=2),
        dbc.Col(create_card("Renewed Total", "card-paid-renewed", color="info"), width=6, md=4, lg=2),
        dbc.Col(create_card("Upgraded Total", "card-paid-upgraded", color="warning"), width=6, md=4, lg=2),
    ], className="mb-2 justify-content-center"),

    # --- Row 2: Bar Graph ---
    dbc.Row([
        dbc.Col([
            dbc.Card([
                #dbc.CardHeader("Daily Paid Subscriptions Trend"),
                dbc.CardBody([
                    dcc.Graph(id='paid-bar-graph', style={'height': '500px'})
                ])
            ], className="shadow-sm glass-container")
        ], width=12)
    ])
], fluid=True)


# --- 2. CALLBACK REGISTRATION ---
def register_callbacks(app):
    # --- Callback A: Populate Dropdown Options ---
    @app.callback(
        [Output('paid-country-dropdown', 'options'),
         Output('paid-type-dropdown', 'options')],
        Input('global-data-store', 'data')
    )
    def update_paid_filter_options(data):
        if not data:
            return [], []

        df = pd.DataFrame(data)

        # 1. Country Options
        country_opts = []
        if 'Location' in df.columns:
            countries = sorted(df['Location'].dropna().unique().astype(str))
            country_opts = [{'label': c, 'value': c} for c in countries]

        # 2. Type Options
        # We only want to show types that are relevant to "Paid" (New, Renewed, Upgraded)
        # to avoid confusion (e.g., don't show 'Trial').
        type_opts = []
        if 'Subscription_Type' in df.columns:
            # Get all types from data
            all_types = df['Subscription_Type'].dropna().unique()
            # Filter to only keep the ones we care about for this page
            valid_paid_labels = ['New', 'Renewed', 'Upgraded']

            # Create options only if they exist in the data (case-insensitive check)
            filtered_types = [t for t in all_types if str(t).title() in valid_paid_labels]
            type_opts = [{'label': str(t).title(), 'value': t} for t in sorted(filtered_types)]

        return country_opts, type_opts

    # --- Callback B: Update Dashboard ---
    @app.callback(
        [
            Output('card-paid-total', 'children'),
            Output('card-paid-revenue', 'children'),
            Output('card-paid-new', 'children'),
            Output('card-paid-renewed', 'children'),
            Output('card-paid-upgraded', 'children'),
            Output('paid-bar-graph', 'figure')
        ],
        [
            Input('global-data-store', 'data'),
            Input('paid-date-picker', 'start_date'),
            Input('paid-date-picker', 'end_date'),
            Input('paid-country-dropdown', 'value'),
            Input('paid-type-dropdown', 'value')  # Added Type Input
        ]
    )
    def update_paid_overview(data, start_date, end_date, selected_countries, selected_types):
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

        # A. Define what constitutes a "Paid" type generally
        base_paid_types = ['new', 'renewed', 'upgraded']

        # B. Determine which types to filter by based on User Selection
        if selected_types:
            # Normalize user selection to lower case
            selected_types_lower = [t.lower() for t in selected_types]
            # Intersect user selection with allowed paid types
            # (This ensures if a user somehow selects 'Trial', it is ignored)
            target_types = [t for t in selected_types_lower if t in base_paid_types]
        else:
            # If no filter selected, use all paid types
            target_types = base_paid_types

        # C. Create Masks
        # 1. Type Mask
        type_mask = df['type_norm'].isin(target_types)

        # 2. Payment Mask (lastPaymentReceivedOn >= Date)
        payment_mask = (df['lastPaymentReceivedOn'] >= df['Date']).fillna(False)

        # D. Apply Masks
        df_paid = df[type_mask & payment_mask].copy()

        # --- 4. APPLY REMAINING FILTERS (Date & Country) ---

        # Date Filter
        if start_date:
            df_paid = df_paid[df_paid['Date'] >= pd.to_datetime(start_date)]
        if end_date:
            df_paid = df_paid[df_paid['Date'] <= pd.to_datetime(end_date)]

        # Country Filter
        if selected_countries:
            if 'Location' in df_paid.columns:
                df_paid = df_paid[df_paid['Location'].isin(selected_countries)]

        # --- 5. CALCULATE PLACARDS ---

        total_paid_count = len(df_paid)
        total_revenue = df_paid['lastAmountPaidEUR'].sum()

        # Breakdown by type (for the specific placards)
        counts = df_paid['type_norm'].value_counts()
        count_new = counts.get('new', 0)
        count_renewed = counts.get('renewed', 0)
        count_upgraded = counts.get('upgraded', 0)

        # --- 6. GENERATE GRAPH ---

        if df_paid.empty:
            fig = px.bar(title="No Paid Subscriptions Found for Selected Filters")
        else:
            df_paid['date_only'] = df_paid['Date'].dt.date

            # Group by Date
            df_grouped = df_paid.groupby('date_only').size().reset_index(name='count')

            # Create Plot
            fig = px.bar(
                df_grouped,
                x='date_only',
                y='count',
                title="Daily Paid Subscriptions",
                labels={'date_only': 'Day', 'count': 'Count of Paid Subs'},
                template="plotly_white",
                color_discrete_sequence=['#198754']
            )

            # Force X-Axis to show ONLY THE DAY (dd)
            fig.update_xaxes(
                dtick="D1",
                tickformat="%d",
                title_text="Day of Month"
            )

            fig.update_layout(hovermode="x unified")

        # Format Revenue
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
