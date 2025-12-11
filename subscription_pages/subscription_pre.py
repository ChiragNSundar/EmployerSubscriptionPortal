import pandas as pd
import numpy as np
import plotly.graph_objs as go
from dash import html, dcc, Input, Output, State
import dash_bootstrap_components as dbc
from prophet import Prophet  # <--- CHANGED: Imported Prophet

# --- CHURN FORECAST LAYOUT ---
churn_forecast_layout = dbc.Container([
    html.H3("AI Churn & Attrition Forecast (Prophet)", className="my-4 text-center text-white"),

    # --- KPI Cards ---
    dbc.Row([
        # Card 1: Total Predicted Churn
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6(id='churn-card-total-title', children="Predicted Churn (Volume)",
                            className="card-title text-muted"),
                    html.H4(id='churn-card-total-pred', children="0", className="text-danger fw-bold")
                ])
            ], className="shadow-sm mb-3")
        ], width=12, md=3),

        # Card 2: Average Daily Churn
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6("Avg Daily Churn", className="card-title text-muted"),
                    html.H4(id='churn-card-avg-pred', children="0", className="text-danger fw-bold")
                ])
            ], className="shadow-sm mb-3")
        ], width=12, md=3),

        # Card 3: Max Churn Spike
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6("Max Churn Spike (1 Day)", className="card-title text-muted"),
                    html.H4(id='churn-card-max-pred', children="0", className="text-dark fw-bold")
                ])
            ], className="shadow-sm mb-3")
        ], width=12, md=3),

        # Card 4: Net Growth Forecast
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6("Projected Net Growth", className="card-title text-muted"),
                    html.H4(id='churn-card-net-pred', children="0", className="text-success fw-bold")
                ])
            ], className="shadow-sm mb-3")
        ], width=12, md=3),
    ]),

    # --- CONTROLS ROW ---
    dbc.Row([
        # Filter: Date Range (History)
        dbc.Col([
            html.Label("Training Data Range:", className="fw-bold"),
            dcc.DatePickerRange(
                id='churn-date-filter',
                display_format='YYYY-MM-DD',
                start_date=None,
                end_date=None,
                style={'zIndex': '2000', 'position': 'relative', 'width': '100%'}
            )
        ], width=12, md=4, className="mb-3"),

        # Input: Days to Predict
        dbc.Col([
            html.Label("Days to Forecast:", className="fw-bold"),
            dbc.Input(id='churn-forecast-days', type='number', value=30, min=7, max=365, step=1)
        ], width=12, md=4, className="mb-3"),

        # Button
        dbc.Col([
            html.Label("Action:", className="fw-bold"),
            dbc.Button("Analyze Churn Risk (Prophet)", id='btn-run-churn-forecast', color="danger", className="w-100")
        ], width=12, md=4, className="mb-3"),

    ], className="mb-4 glass-container", style={'zIndex': '1000', 'position': 'relative'}),

    # --- GRAPH ROW ---
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    dcc.Loading(
                        id="loading-churn-forecast",
                        type="default",
                        children=dcc.Graph(id='churn-forecast-graph', style={'height': '500px'})
                    )
                ])
            ], className="shadow-sm glass-container")
        ], width=12)
    ])
], fluid=True)


# --- HELPER FUNCTION: CHURN PREDICTION LOGIC (PROPHET) ---
def get_churn_prediction(df_in, days_to_predict):
    df = df_in.copy()

    # 1. Clean Dates
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    df = df.dropna(subset=['Date'])
    if df.empty: return None

    # 2. Categorize: Churn vs Inflow
    df['type_norm'] = df['Subscription_Type'].str.lower().str.strip()

    # Define Churn
    df['is_churn'] = df['type_norm'].isin(['cancelled', 'canceled', 'cancellation'])

    # Define Inflow (Growth)
    df['is_inflow'] = df['type_norm'].isin(['new', 'renewed', 'upgraded'])

    # 3. Group by Day
    daily_stats = df.groupby(pd.Grouper(key='Date', freq='D')).agg(
        churn_count=('is_churn', 'sum'),
        inflow_count=('is_inflow', 'sum')
    ).reset_index()

    # We need enough data points (Prophet prefers at least ~2 weeks of data)
    if len(daily_stats) < 10: return None

    # --- 4. PREPARE DATA FOR PROPHET ---
    # Prophet requires columns: 'ds' (date) and 'y' (value)

    # Data for Churn Model
    df_prophet_churn = pd.DataFrame({
        'ds': daily_stats['Date'],
        'y': daily_stats['churn_count']
    })

    # Data for Inflow Model
    df_prophet_inflow = pd.DataFrame({
        'ds': daily_stats['Date'],
        'y': daily_stats['inflow_count']
    })

    # --- 5. TRAIN MODELS ---

    # Model A: Churn
    # daily_seasonality=True helps with daily data patterns
    m_churn = Prophet(daily_seasonality=True, yearly_seasonality=False, weekly_seasonality=True)
    m_churn.fit(df_prophet_churn)

    # Model B: Inflow
    m_inflow = Prophet(daily_seasonality=True, yearly_seasonality=False, weekly_seasonality=True)
    m_inflow.fit(df_prophet_inflow)

    # --- 6. PREDICT FUTURE ---

    # Create future dataframe
    future_churn = m_churn.make_future_dataframe(periods=int(days_to_predict))
    future_inflow = m_inflow.make_future_dataframe(periods=int(days_to_predict))

    # Forecast
    forecast_churn = m_churn.predict(future_churn)
    forecast_inflow = m_inflow.predict(future_inflow)

    # Extract only the future part for metrics
    # The forecast dataframe contains history + future. We slice the last 'days_to_predict' rows.
    future_churn_only = forecast_churn.tail(int(days_to_predict))
    future_inflow_only = forecast_inflow.tail(int(days_to_predict))

    # Get values (yhat)
    pred_churn = future_churn_only['yhat'].values
    pred_inflow = future_inflow_only['yhat'].values
    future_dates = future_churn_only['ds'].values

    # Clean Predictions (No negatives, round to integers)
    pred_churn = np.round(np.maximum(pred_churn, 0))
    pred_inflow = np.round(np.maximum(pred_inflow, 0))

    # 7. Calculate Metrics
    total_pred_churn = np.sum(pred_churn)
    avg_daily_churn = np.mean(pred_churn)
    max_churn_spike = np.max(pred_churn)

    total_pred_inflow = np.sum(pred_inflow)
    net_growth = total_pred_inflow - total_pred_churn

    return {
        'metrics': (total_pred_churn, avg_daily_churn, max_churn_spike, net_growth),
        'dates': future_dates,
        'preds': (pred_churn, pred_inflow),
        'history': daily_stats
    }


# --- CALLBACKS ---
def register_churn_callbacks(app):
    @app.callback(
        [Output('churn-card-total-pred', 'children'),
         Output('churn-card-avg-pred', 'children'),
         Output('churn-card-max-pred', 'children'),
         Output('churn-card-net-pred', 'children'),
         Output('churn-card-net-pred', 'className'),  # To change color (Green/Red)
         Output('churn-forecast-graph', 'figure'),
         Output('churn-card-total-title', 'children')],
        [Input('btn-run-churn-forecast', 'n_clicks')],
        [State('global-data-store', 'data'),
         State('churn-forecast-days', 'value'),
         State('churn-date-filter', 'start_date'),
         State('churn-date-filter', 'end_date')]
    )
    def update_churn_forecast(n_clicks, data, days, start_date, end_date):
        # Default / Empty State
        empty_fig = go.Figure().update_layout(
            title="Click 'Analyze Churn Risk' to generate forecast",
            xaxis={'visible': False}, yaxis={'visible': False}
        )
        if not data or n_clicks is None:
            return "0", "0", "0", "0", "text-success fw-bold", empty_fig, "Predicted Churn (Volume)"

        df = pd.DataFrame(data)

        # --- 1. DATA MAPPING ---
        if 'lastPaymentReceivedOn' in df.columns:
            df['Date'] = pd.to_datetime(df['lastPaymentReceivedOn'], errors='coerce')
        elif 'dateUTC' in df.columns:
            df['Date'] = pd.to_datetime(df['dateUTC'], errors='coerce')
        elif 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        else:
            return "0", "0", "0", "0", "text-muted", empty_fig, "Error: No Date Column"

        if 'Subscription_Type' in df.columns:
            df['Subscription_Type'] = df['Subscription_Type'].astype(str)
        elif 'type' in df.columns:
            df['Subscription_Type'] = df['type'].astype(str)
        else:
            return "0", "0", "0", "0", "text-muted", empty_fig, "Error: No Type Column"

        # --- 2. FILTERING ---
        df = df.dropna(subset=['Date'])

        if start_date and end_date:
            df = df[(df['Date'] >= start_date) & (df['Date'] <= end_date)]

        # --- 3. RUN PREDICTION ---
        result = get_churn_prediction(df, days)

        if not result:
            return "N/A", "N/A", "N/A", "N/A", "text-muted", empty_fig, "Insufficient Data"

        (tot_churn, avg_churn, max_churn, net_growth) = result['metrics']
        f_dates = result['dates']
        (p_churn, p_inflow) = result['preds']
        hist_df = result['history']

        # --- 4. FORMATTING ---
        fmt_tot = f"{int(tot_churn):,}"
        fmt_avg = f"{avg_churn:.1f}"
        fmt_max = f"{int(max_churn):,}"
        fmt_net = f"{int(net_growth):,}"

        # Dynamic Color for Net Growth
        net_class = "text-success fw-bold" if net_growth >= 0 else "text-danger fw-bold"
        if net_growth > 0: fmt_net = f"+{fmt_net}"

        # --- 5. GENERATE GRAPH ---
        fig = go.Figure()

        # A. Historical Churn (Actual)
        fig.add_trace(go.Scatter(
            x=hist_df['Date'],
            y=hist_df['churn_count'],
            mode='lines',
            name='Historical Churn',
            line=dict(color='#dc3545', width=2),  # Red
            fill='tozeroy',
            fillcolor='rgba(220, 53, 69, 0.1)'
        ))

        # B. Predicted Churn (Forecast)
        fig.add_trace(go.Scatter(
            x=f_dates,
            y=p_churn,
            mode='lines',
            name='Predicted Churn (Prophet)',
            line=dict(color='#dc3545', width=3, dash='dot'),
            hoverinfo='x+y'
        ))

        # C. Predicted Inflow (Context)
        fig.add_trace(go.Scatter(
            x=f_dates,
            y=p_inflow,
            mode='lines',
            name='Predicted Inflow (Prophet)',
            line=dict(color='#198754', width=2, dash='dot'),  # Green
            hoverinfo='x+y'
        ))

        # D. Connector Line
        fig.add_trace(go.Scatter(
            x=[hist_df['Date'].iloc[-1], f_dates[0]],
            y=[hist_df['churn_count'].iloc[-1], p_churn[0]],
            mode='lines',
            showlegend=False,
            line=dict(color='#dc3545', width=2, dash='dot'),
            hoverinfo='skip'
        ))

        fig.update_layout(
            title="Churn Risk Analysis: Historical vs Prophet Forecast",
            xaxis_title="Date",
            yaxis_title="Volume of Cancellations",
            template="plotly_white",
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )

        title_suffix = f"(Next {days} Days)"

        return fmt_tot, fmt_avg, fmt_max, fmt_net, net_class, fig, f"Predicted Churn {title_suffix}"