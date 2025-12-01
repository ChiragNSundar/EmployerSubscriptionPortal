import pandas as pd
import plotly.graph_objects as go
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
    html.H3("Subscription Payment Overview (Comparison)", className="my-4 text-center"),

    # --- Row 0: Filters ---
    dbc.Row([
        # 1. Date Range Picker
        dbc.Col([
            html.Label("Select Date Range:", className="control-label"),
            html.Div(
                dcc.DatePickerRange(
                    id='cmp-date-picker',
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
                id='cmp-country-dropdown',
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
                id='cmp-type-dropdown',
                options=[],
                multi=True,
                placeholder="All Types",
                className="mb-3"
            )
        ], width=12, md=4),

    ], className="mb-4  glass-container", style={'position': 'relative', 'zIndex': '1000'}),

    # --- Row 1: Placards (4 Cards) ---
    dbc.Row([
        dbc.Col(create_card("Total(Paid+Unpaid)", "cmp-card-total-all", color="dark"), width=6, md=3),
        dbc.Col(create_card("Total Paid Subs", "cmp-card-total-paid", color="success"), width=6, md=3),
        dbc.Col(create_card("Paid Percentage (%)", "cmp-card-paid-percent", color="info"), width=6, md=3),
        dbc.Col(create_card("Total Revenue EUR(€)", "cmp-card-total-revenue", color="warning"), width=6, md=3),
    ], className="mb-2 justify-content-center"),

    # --- Row 2: Combined Graph ---
    dbc.Row([
        dbc.Col([
            dbc.Card([
                #dbc.CardHeader("Daily Trend: Total vs Paid & Paid %"),
                dbc.CardBody([
                    dcc.Graph(id='cmp-paid-bar-graph', style={'height': '500px'})
                ])
            ], className="shadow-sm glass-container")
        ], width=12)
    ])
], fluid=True)


# --- 2. CALLBACK REGISTRATION ---
def register_callbacks(app):
    # --- Callback A: Populate Dropdown Options ---
    @app.callback(
        [Output('cmp-country-dropdown', 'options'),
         Output('cmp-type-dropdown', 'options')],
        Input('global-data-store', 'data')
    )
    def update_cmp_filter_options(data):
        if not data:
            return [], []

        df = pd.DataFrame(data)

        # 1. Country Options
        country_opts = []
        if 'Location' in df.columns:
            countries = sorted(df['Location'].dropna().unique().astype(str))
            country_opts = [{'label': c, 'value': c} for c in countries]

        # 2. Type Options
        type_opts = []
        if 'Subscription_Type' in df.columns:
            all_types = sorted(df['Subscription_Type'].dropna().unique().astype(str))
            type_opts = [{'label': t.title(), 'value': t} for t in all_types]

        return country_opts, type_opts

    # --- Callback B: Update Dashboard ---
    @app.callback(
        [
            Output('cmp-card-total-all', 'children'),
            Output('cmp-card-total-paid', 'children'),
            Output('cmp-card-paid-percent', 'children'),
            Output('cmp-card-total-revenue', 'children'),
            Output('cmp-paid-bar-graph', 'figure')
        ],
        [
            Input('global-data-store', 'data'),
            Input('cmp-date-picker', 'start_date'),
            Input('cmp-date-picker', 'end_date'),
            Input('cmp-country-dropdown', 'value'),
            Input('cmp-type-dropdown', 'value')
        ]
    )
    def update_cmp_overview(data, start_date, end_date, selected_countries, selected_types):
        # 1. Handle Empty Data
        empty_fig = go.Figure()
        empty_fig.update_layout(title="No Data Available")
        if not data:
            return "0", "0", "0%", "€ 0", empty_fig

        df = pd.DataFrame(data)

        # 2. Data Pre-processing
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')

        if 'lastPaymentReceivedOn' in df.columns:
            df['lastPaymentReceivedOn'] = pd.to_datetime(df['lastPaymentReceivedOn'], errors='coerce')
        else:
            df['lastPaymentReceivedOn'] = pd.NaT

        if 'lastAmountPaidEUR' in df.columns:
            df['lastAmountPaidEUR'] = pd.to_numeric(df['lastAmountPaidEUR'], errors='coerce').fillna(0)
        else:
            df['lastAmountPaidEUR'] = 0

        if 'Subscription_Type' in df.columns:
            df['type_norm'] = df['Subscription_Type'].astype(str).str.lower()
        else:
            df['type_norm'] = "unknown"

        # --- 3. DETERMINE PAID STATUS ---
        paid_types = ['new', 'renewed', 'upgraded']

        # Paid Logic: Type is correct AND Payment Date >= Subscription Date
        is_paid_type = df['type_norm'].isin(paid_types)
        has_valid_payment = (df['lastPaymentReceivedOn'] >= df['Date']).fillna(False)

        df['is_paid'] = is_paid_type & has_valid_payment

        # --- 4. APPLY FILTERS ---
        if start_date:
            df = df[df['Date'] >= pd.to_datetime(start_date)]
        if end_date:
            df = df[df['Date'] <= pd.to_datetime(end_date)]

        if selected_countries:
            if 'Location' in df.columns:
                df = df[df['Location'].isin(selected_countries)]

        if selected_types:
            df = df[df['Subscription_Type'].isin(selected_types)]

        # --- 5. CALCULATE PLACARDS ---
        total_all = len(df)
        total_paid = df['is_paid'].sum()
        total_revenue = df.loc[df['is_paid'], 'lastAmountPaidEUR'].sum()

        if total_all > 0:
            paid_percent = (total_paid / total_all) * 100
        else:
            paid_percent = 0

        # --- 6. GENERATE GRAPH ---
        if df.empty:
            fig = go.Figure()
            fig.update_layout(title="No Data Found for Selected Filters")
        else:
            df['date_only'] = df['Date'].dt.date

            # Group by Date
            df_grouped = df.groupby('date_only').agg(
                Total_Count=('is_paid', 'count'),
                Paid_Count=('is_paid', 'sum')
            ).reset_index()

            df_grouped['Paid_Percentage'] = (df_grouped['Paid_Count'] / df_grouped['Total_Count']) * 100

            # Create text labels for the scatter plot (e.g., "45%")
            # We only show label if percentage > 0 to avoid cluttering 0% lines
            df_grouped['Percent_Text'] = df_grouped['Paid_Percentage'].apply(lambda x: f"{x:.0f}%" if x > 0 else "")

            fig = go.Figure()

            # Bar: Total (Dark Blue)
            fig.add_trace(go.Bar(
                x=df_grouped['date_only'],
                y=df_grouped['Total_Count'],
                name='Total',
                marker_color='#2c3e50',  # Dark Blue / Slate
                opacity=0.7,
                yaxis='y1'
            ))

            # Bar: Paid (Teal)
            fig.add_trace(go.Bar(
                x=df_grouped['date_only'],
                y=df_grouped['Paid_Count'],
                name='Paid Subs',
                marker_color='#20c997',  # Teal / Sea Green
                yaxis='y1'
            ))

            # Line: Percentage (Orange/Red with Text)
            fig.add_trace(go.Scatter(
                x=df_grouped['date_only'],
                y=df_grouped['Paid_Percentage'],
                name='Paid %',
                mode='lines+markers+text',  # Added text mode
                text=df_grouped['Percent_Text'],  # The labels
                textposition='top center',  # Position above the dot
                textfont=dict(color='#d63384', size=10, weight='bold'),  # Pink/Red text
                line=dict(color='#d63384', width=3),  # Pink/Red line
                marker=dict(size=8, color='#d63384'),
                yaxis='y2'
            ))

            fig.update_layout(
                title="Daily Subscriptions: Total vs Paid",
                xaxis_title="Day of Month",
                yaxis=dict(title="Count", side="left"),
                yaxis2=dict(
                    title="Paid %",
                    side="right",
                    overlaying="y",
                    range=[0, 115],  # Slightly higher to fit text labels
                    showgrid=False
                ),
                barmode='group',
                legend=dict(x=0.01, y=1.1, orientation='h'),
                template="plotly_white",
                hovermode="x unified"
            )

            fig.update_xaxes(dtick="D1", tickformat="%d", title_text="Day of Month")

        return (
            f"{total_all:,}",
            f"{total_paid:,}",
            f"{paid_percent:.1f}%",
            f"€ {total_revenue:,.2f}",
            fig
        )