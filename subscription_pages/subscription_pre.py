import pandas as pd
import numpy as np
import plotly.graph_objs as go
from dash import html, dcc, Input, Output, State
import dash_bootstrap_components as dbc
from sklearn.ensemble import RandomForestRegressor

# --- EMPLOYEE COUNT FORECAST LAYOUT ---
employee_forecast_layout = dbc.Container([
    html.H3("AI Employee Subscription Forecasting (Volume)", className="my-4 text-center text-white"),

    # --- KPI Cards (Row 1: Total, New, Renewed) ---
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6(id='emp-card-total-title', children="Total Activity", className="card-title text-muted"),
                    html.H4(id='emp-card-total-pred', children="0", className="text-primary fw-bold")
                ])
            ], className="shadow-sm mb-3")
        ], width=12, md=4),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6(id='emp-card-new-title', children="New Employees", className="card-title text-muted"),
                    html.H4(id='emp-card-new-pred', children="0", className="text-success fw-bold")
                ])
            ], className="shadow-sm mb-3")
        ], width=12, md=4),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6(id='emp-card-renewed-title', children="Renewed Employees",
                            className="card-title text-muted"),
                    html.H4(id='emp-card-renewed-pred', children="0", className="text-info fw-bold")
                ])
            ], className="shadow-sm mb-3")
        ], width=12, md=4),
    ]),

    # --- KPI Cards (Row 2: Upgraded, Trial, Cancelled) ---
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6(id='emp-card-upgraded-title', children="Upgraded Employees",
                            className="card-title text-muted"),
                    html.H4(id='emp-card-upgraded-pred', children="0", className="text-warning fw-bold")
                ])
            ], className="shadow-sm mb-3")
        ], width=12, md=4),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6(id='emp-card-trial-title', children="Trial Employees", className="card-title text-muted"),
                    html.H4(id='emp-card-trial-pred', children="0", className="text-secondary fw-bold")
                ])
            ], className="shadow-sm mb-3")
        ], width=12, md=4),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6(id='emp-card-cancelled-title', children="Cancelled Employees",
                            className="card-title text-muted"),
                    html.H4(id='emp-card-cancelled-pred', children="0", className="text-danger fw-bold")
                ])
            ], className="shadow-sm mb-3")
        ], width=12, md=4),
    ], className="mb-2"),

    # --- NEW FILTERS ROW (Date Range & Type) ---
    dbc.Row([
        # Filter 1: Date Range
        dbc.Col([
            html.Label("Filter History Date Range:", className="fw-bold"),
            html.Br(),
            dcc.DatePickerRange(
                id='emp-date-filter',
                display_format='YYYY-MM-DD',
                start_date=None,
                end_date=None,
                # FIX 1: Ensure the calendar popup floats above other elements
                style={'zIndex': '2000', 'position': 'relative', 'width': '100%'}
            )
        ],
            width=12, md=6,
            className="mb-3",
            # FIX 2: High z-index for the column holding the date picker
            style={'zIndex': '1050', 'position': 'relative'}
        ),

        # Filter 2: Subscription Type
        dbc.Col([
            html.Label("Filter Subscription Types:", className="fw-bold"),
            dcc.Dropdown(
                id='emp-type-filter',
                options=[
                    {'label': 'New', 'value': 'new'},
                    {'label': 'Renewed', 'value': 'renewed'},
                    {'label': 'Upgraded', 'value': 'upgraded'},
                    {'label': 'Trial', 'value': 'trial'},
                    {'label': 'Cancelled', 'value': 'cancelled'}
                ],
                value=[],
                multi=True,
                placeholder="Select types (Default: All)",
                # FIX 3: High z-index for the dropdown element itself
                style={'zIndex': '2000', 'position': 'relative'}
            )
        ],
            width=12, md=6,
            className="mb-3",
            # FIX 4: CRITICAL! 'overflow: visible' lets the menu hang outside the box
            style={'zIndex': '1050', 'position': 'relative', 'overflow': 'visible'}
        ),
    ],
        className="mb-2 glass-container",
        # FIX 5: Ensure the Row also allows overflow and sits above the row below it
        style={'overflow': 'visible', 'position': 'relative', 'zIndex': '1050'}
    ),

    # --- Controls Row (Days & Button) ---
    dbc.Row([
        # --- COLUMN 1: DAYS INPUT ---
        dbc.Col([
            html.Label("Days to Predict:", className="fw-bold"),
            dbc.Input(id='emp-forecast-days', type='number', value=30, min=7, max=365, step=1)
        ], width=12, md=6, style={'zIndex': '1000', 'position': 'relative'}),

        # --- COLUMN 2: BUTTON ---
        dbc.Col([
            html.Br(),
            dbc.Button("Generate Employee Forecast", id='btn-run-emp-forecast', color="primary", className="w-100")
        ], width=12, md=6, style={'zIndex': '1000', 'position': 'relative'}),

    ],
        className="mb-4 glass-container",
        style={'overflow': 'visible', 'position': 'relative', 'zIndex': '1000'}
    ),

    # --- GRAPH ROW ---
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    dcc.Loading(
                        id="loading-emp-forecast",
                        type="default",
                        children=dcc.Graph(id='emp-forecast-graph', style={'height': '500px'})
                    )
                ])
            ],
                className="shadow-sm glass-container",
                style={'zIndex': '1', 'position': 'relative'}
            )
        ], width=12)
    ])
], fluid=True)


# --- HELPER FUNCTION: PREDICTION LOGIC ---
def get_employee_count_prediction(df_in, days_to_predict):
    df = df_in.copy()

    # 1. Clean Dates
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    df = df.dropna(subset=['Date'])

    if df.empty: return None

    # 2. Group Data (COUNT ONLY)
    df_grouped = df.groupby([pd.Grouper(key='Date', freq='D'), 'Subscription_Type']).size().reset_index(name='count')

    # Pivot: Date is Index, Columns are Types, Values are Counts
    df_pivot = df_grouped.pivot(index='Date', columns='Subscription_Type', values='count').fillna(0)

    # --- Ensure all 5 columns exist ---
    required_cols = ['new', 'renewed', 'upgraded', 'trial', 'cancelled']
    for col in required_cols:
        if col not in df_pivot.columns:
            df_pivot[col] = 0

    # 3. Prepare Features (X) and Targets (y)
    df_pivot['day_of_week'] = df_pivot.index.dayofweek
    df_pivot['day_of_month'] = df_pivot.index.day
    df_pivot['month'] = df_pivot.index.month
    df_pivot['trend_index'] = np.arange(len(df_pivot))

    features = ['day_of_week', 'day_of_month', 'month', 'trend_index']
    X = df_pivot[features]
    y = df_pivot[required_cols]  # Predicting counts for all 5 types

    # 4. Train Model
    if len(df_pivot) < 5: return None

    rf_model = RandomForestRegressor(n_estimators=500, random_state=42)
    rf_model.fit(X, y)

    # 5. Predict Future
    last_date = df_pivot.index.max()
    future_dates = [last_date + pd.Timedelta(days=x) for x in range(1, int(days_to_predict) + 1)]

    future_df = pd.DataFrame({'Date': future_dates})
    future_df['day_of_week'] = future_df['Date'].dt.dayofweek
    future_df['day_of_month'] = future_df['Date'].dt.day
    future_df['month'] = future_df['Date'].dt.month

    last_index = df_pivot['trend_index'].max()
    future_df['trend_index'] = np.arange(last_index + 1, last_index + 1 + len(future_dates))

    # Predict
    predictions = rf_model.predict(future_df[features])
    predictions = np.maximum(predictions, 0)  # No negatives

    # Round predictions to nearest whole number
    predictions = np.round(predictions)

    # 6. Organize Results
    preds_new = predictions[:, 0]
    preds_renewed = predictions[:, 1]
    preds_upgraded = predictions[:, 2]
    preds_trial = predictions[:, 3]
    preds_cancelled = predictions[:, 4]

    # Calculate Total Activity (Sum of predictions)
    preds_total = preds_new + preds_renewed + preds_upgraded + preds_trial + preds_cancelled

    # Prepare History Data (Sum of actuals)
    df_pivot['total'] = df_pivot['new'] + df_pivot['renewed'] + df_pivot['upgraded'] + df_pivot['trial'] + df_pivot[
        'cancelled']
    hist_df = df_pivot.reset_index()

    return {
        'sums': (sum(preds_total), sum(preds_new), sum(preds_renewed), sum(preds_upgraded), sum(preds_trial),
                 sum(preds_cancelled)),
        'dates': future_dates,
        'preds': (preds_total, preds_new, preds_renewed, preds_upgraded, preds_trial, preds_cancelled),
        'history': hist_df
    }


# --- CALLBACKS ---
def register_employee_callbacks(app):
    @app.callback(
        [Output('emp-card-total-pred', 'children'),
         Output('emp-card-new-pred', 'children'),
         Output('emp-card-renewed-pred', 'children'),
         Output('emp-card-upgraded-pred', 'children'),
         Output('emp-card-trial-pred', 'children'),
         Output('emp-card-cancelled-pred', 'children'),
         Output('emp-forecast-graph', 'figure'),
         Output('emp-card-total-title', 'children'),
         Output('emp-card-new-title', 'children'),
         Output('emp-card-renewed-title', 'children'),
         Output('emp-card-upgraded-title', 'children'),
         Output('emp-card-trial-title', 'children'),
         Output('emp-card-cancelled-title', 'children')],
        [Input('btn-run-emp-forecast', 'n_clicks')],
        [State('global-data-store', 'data'),
         State('emp-forecast-days', 'value'),
         State('emp-date-filter', 'start_date'),  # NEW: Start Date
         State('emp-date-filter', 'end_date'),  # NEW: End Date
         State('emp-type-filter', 'value')]  # NEW: Selected Types
    )
    def update_employee_forecast(n_clicks, data, days, start_date, end_date, selected_types):
        # Default Empty State
        empty_res = ("-", "-", "-", "-", "-", "-", go.Figure().update_layout(title="No Data"),
                     "Total", "New", "Renewed", "Upgraded", "Trial", "Cancelled")

        if not data: return empty_res
        if n_clicks is None:
            return "0", "0", "0", "0", "0", "0", go.Figure().update_layout(
                title="Click 'Generate Forecast' to see predictions",
                xaxis={'visible': False}, yaxis={'visible': False}
            ), "Total", "New", "Renewed", "Upgraded", "Trial", "Cancelled"

        df = pd.DataFrame(data)

        # --- 1. DATA CLEANING ---
        if 'lastPaymentReceivedOn' in df.columns:
            df['Date'] = pd.to_datetime(df['lastPaymentReceivedOn'], errors='coerce')
        elif 'dateUTC' in df.columns:
            df['Date'] = pd.to_datetime(df['dateUTC'], errors='coerce')
        elif 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        else:
            return empty_res

        if 'Subscription_Type' in df.columns:
            df['Subscription_Type'] = df['Subscription_Type'].astype(str)
        elif 'type' in df.columns:
            df['Subscription_Type'] = df['type'].astype(str)
        else:
            return empty_res

        # --- 2. BASIC FILTERING ---
        df['Subscription_Type'] = df['Subscription_Type'].str.lower().str.strip()
        df['Subscription_Type'] = df['Subscription_Type'].replace(
            {'canceled': 'cancelled', 'cancellation': 'cancelled'})

        valid_types = ['new', 'renewed', 'upgraded', 'trial', 'cancelled']
        mask_type = df['Subscription_Type'].isin(valid_types)
        mask_date = df['Date'].notna()

        df_clean = df[mask_type & mask_date].copy()

        # --- 3. APPLY USER FILTERS (NEW LOGIC) ---

        # A. Date Range Filter
        if start_date and end_date:
            df_clean = df_clean[(df_clean['Date'] >= start_date) & (df_clean['Date'] <= end_date)]

        # B. Subscription Type Filter
        # If user selected specific types (and list is not empty), filter the dataframe.
        # If list is empty, we assume "All" (default behavior).
        if selected_types and len(selected_types) > 0:
            df_clean = df_clean[df_clean['Subscription_Type'].isin(selected_types)]

        # --- 4. RUN PREDICTION ---
        result = get_employee_count_prediction(df_clean, days)

        if not result:
            return empty_res

        (s_tot, s_new, s_ren, s_upg, s_tri, s_can) = result['sums']
        f_dates = result['dates']
        (p_tot, p_new, p_ren, p_upg, p_tri, p_can) = result['preds']
        hist_df = result['history']

        def fmt(val):
            return f"{int(val):,}"

        # --- 5. GENERATE GRAPH ---
        fig = go.Figure()

        # Helper to add traces
        def add_traces(hist_col, pred_vals, name, color, is_main_line=False):

            # If it's the main line (Total), make it thick and visible.
            # If it's a sub-type, make width=0 (invisible line) but keep data for hover.
            line_width = 3 if is_main_line else 0
            show_legend = True if is_main_line else False

            # History Trace
            fig.add_trace(go.Scatter(
                x=hist_df['Date'],
                y=hist_df[hist_col],
                mode='lines',
                name=f"{name} (Actual)",
                line=dict(color=color, width=line_width),
                showlegend=show_legend,
                hoverinfo='x+name+y'
            ))

            # Prediction Trace
            fig.add_trace(go.Scatter(
                x=f_dates,
                y=pred_vals,
                mode='lines',
                name=f"{name} (Pred)",
                line=dict(color='red', width=line_width, dash='dash'),
                showlegend=show_legend,
                hoverinfo='x+name+y'
            ))

            # Connector Trace (Only needed for the visible Total line)
            if is_main_line and len(pred_vals) > 0:
                fig.add_trace(go.Scatter(
                    x=[hist_df['Date'].iloc[-1], f_dates[0]],
                    y=[hist_df[hist_col].iloc[-1], pred_vals[0]],
                    mode='lines',
                    showlegend=False,
                    line=dict(color=color, width=line_width, dash='dash'),
                    hoverinfo='skip'
                ))

        # --- ADD TRACES ---

        # 1. Add TOTAL (Visible Line)
        add_traces('total', p_tot, "Total", "#0d6efd", is_main_line=True)

        # 2. Add SUB-TYPES (Invisible Lines, but data exists for Hover)
        add_traces('new', p_new, "New", "#198754", is_main_line=False)
        add_traces('renewed', p_ren, "Renewed", "#0dcaf0", is_main_line=False)
        add_traces('upgraded', p_upg, "Upgraded", "#ffc107", is_main_line=False)
        add_traces('trial', p_tri, "Trial", "#6f42c1", is_main_line=False)
        add_traces('cancelled', p_can, "Cancelled", "#dc3545", is_main_line=False)

        # --- UPDATE LAYOUT & DATE FORMAT ---
        fig.update_layout(
            title=f"Daily Employee Subscription Forecast (Total Volume)",
            xaxis_title="Date",
            yaxis_title="Number of Employees",
            template="plotly_white",
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )

        fig.update_xaxes(hoverformat='%b %d, %Y')

        t_suffix = f"(Next {days} Days)"

        return (fmt(s_tot), fmt(s_new), fmt(s_ren), fmt(s_upg), fmt(s_tri), fmt(s_can), fig,
                f"Total {t_suffix}", f"New {t_suffix}", f"Renewed {t_suffix}",
                f"Upgraded {t_suffix}", f"Trial {t_suffix}", f"Cancelled {t_suffix}")