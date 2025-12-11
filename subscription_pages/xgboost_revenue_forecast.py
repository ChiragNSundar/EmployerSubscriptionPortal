import pandas as pd
import numpy as np
import plotly.graph_objs as go
from dash import html, dcc, Input, Output, State
import dash_bootstrap_components as dbc
from xgboost import XGBRegressor

# =============================================================================
# 1. LAYOUT DEFINITION
# =============================================================================
xgboost_revenue_layout = dbc.Container([
    html.H3("AI Revenue Forecasting (XGBoost)", className="my-4 text-center"),

    # --- KPI Cards Row ---
    dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Total Revenue Predicted", className="text-muted"),
            html.H4(id='xgb-rev-total', children="€0.00", className="text-primary fw-bold")
        ]), className="shadow-sm mb-3"), width=6, md=3),

        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("New Revenue Predicted", className="text-muted"),
            html.H4(id='xgb-rev-new', children="€0.00", className="text-success fw-bold")
        ]), className="shadow-sm mb-3"), width=6, md=3),

        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Renewed Revenue Predicted", className="text-muted"),
            html.H4(id='xgb-rev-renewed', children="€0.00", className="text-info fw-bold")
        ]), className="shadow-sm mb-3"), width=6, md=3),

        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Upgraded Revenue Predicted", className="text-muted"),
            html.H4(id='xgb-rev-upgraded', children="€0.00", className="text-warning fw-bold")
        ]), className="shadow-sm mb-3"), width=6, md=3),
    ], className="mb-2"),

    # --- Controls Row ---
    dbc.Row([
        dbc.Col([
            html.Label("Days to Predict:", className="fw-bold"),
            dbc.Input(id='xgb-rev-days', type='number', value=30, min=7, max=365)
        ], width=12, md=6),

        dbc.Col([
            html.Br(),
            dbc.Button("Generate XGBoost Forecast", id='btn-run-xgb-rev', color="primary", className="w-100")
        ], width=12, md=6),
    ], className="mb-4"),

    # --- Graph Row ---
    dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody(
            dcc.Loading(dcc.Graph(id='xgb-rev-graph', style={'height': '500px'}))
        )), width=12)
    ])
], fluid=True)


# =============================================================================
# 2. LOGIC & PREDICTION FUNCTIONS
# =============================================================================
def get_xgboost_revenue_prediction(df_in, days_to_predict):
    df = df_in.copy()

    # Ensure Date format
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    df = df.dropna(subset=['Date'])

    if df.empty: return None

    # Remove Outliers (IQR Method)
    if len(df) > 20:
        Q1 = df['Revenue'].quantile(0.25)
        Q3 = df['Revenue'].quantile(0.75)
        IQR = Q3 - Q1
        df = df[(df['Revenue'] >= (Q1 - 1.5 * IQR)) & (df['Revenue'] <= (Q3 + 1.5 * IQR))]

    # Group Data by Day and Type
    df_grouped = df.groupby([pd.Grouper(key='Date', freq='D'), 'Subscription_Type'])['Revenue'].sum().reset_index()

    # Pivot to get columns: Date, New, Renewed, Upgraded
    df_pivot = df_grouped.pivot(index='Date', columns='Subscription_Type', values='Revenue').fillna(0)

    # Ensure required columns exist
    required_cols = ['New', 'Renewed', 'Upgraded']
    for col in required_cols:
        if col not in df_pivot.columns:
            df_pivot[col] = 0

    # Feature Engineering (Time-based features)
    df_pivot['day_of_week'] = df_pivot.index.dayofweek
    df_pivot['day_of_month'] = df_pivot.index.day
    df_pivot['month'] = df_pivot.index.month
    df_pivot['trend_index'] = np.arange(len(df_pivot))

    features = ['day_of_week', 'day_of_month', 'month', 'trend_index']
    X = df_pivot[features]

    if len(df_pivot) < 5: return None

    # Prepare Future Dataframe
    last_date = df_pivot.index.max()
    future_dates = [last_date + pd.Timedelta(days=x) for x in range(1, int(days_to_predict) + 1)]

    future_df = pd.DataFrame({'Date': future_dates})
    future_df['day_of_week'] = future_df['Date'].dt.dayofweek
    future_df['day_of_month'] = future_df['Date'].dt.day
    future_df['month'] = future_df['Date'].dt.month

    # Continue the trend index
    last_index_val = df_pivot['trend_index'].max()
    future_df['trend_index'] = np.arange(last_index_val + 1, last_index_val + 1 + len(future_dates))

    predictions = {}

    # Train XGBoost for each revenue stream
    for col in required_cols:
        model = XGBRegressor(n_estimators=200, learning_rate=0.1, max_depth=3, random_state=42)
        model.fit(X, df_pivot[col])
        preds = model.predict(future_df[features])
        predictions[col] = np.maximum(preds, 0)  # Ensure no negative revenue

    # Aggregate Totals
    preds_total = predictions['New'] + predictions['Renewed'] + predictions['Upgraded']
    df_pivot['Total'] = df_pivot['New'] + df_pivot['Renewed'] + df_pivot['Upgraded']

    return {
        'sums': (sum(preds_total), sum(predictions['New']), sum(predictions['Renewed']), sum(predictions['Upgraded'])),
        'dates': future_dates,
        'preds': (preds_total, predictions['New'], predictions['Renewed'], predictions['Upgraded']),
        'history': df_pivot.reset_index()
    }


# =============================================================================
# 3. CALLBACK REGISTRATION
# =============================================================================
def register_xgboost_revenue_callbacks(app):
    @app.callback(
        [Output('xgb-rev-total', 'children'), Output('xgb-rev-new', 'children'),
         Output('xgb-rev-renewed', 'children'), Output('xgb-rev-upgraded', 'children'),
         Output('xgb-rev-graph', 'figure')],
        [Input('btn-run-xgb-rev', 'n_clicks')],
        [State('global-data-store', 'data'), State('xgb-rev-days', 'value')]
    )
    def update_forecast(n_clicks, data, days):
        if not data or n_clicks is None:
            return "€0.00", "€0.00", "€0.00", "€0.00", go.Figure()

        df = pd.DataFrame(data)

        # --- Data Cleaning & Mapping ---
        if 'lastPaymentReceivedOn' in df.columns:
            df['Date'] = pd.to_datetime(df['lastPaymentReceivedOn'], errors='coerce')
        elif 'dateUTC' in df.columns:
            df['Date'] = pd.to_datetime(df['dateUTC'], errors='coerce')

        if 'lastAmountPaidEUR' in df.columns:
            df['Revenue'] = pd.to_numeric(df['lastAmountPaidEUR'], errors='coerce').fillna(0)

        # Normalize Subscription Type
        if 'Subscription_Type' in df.columns:
            df['Subscription_Type'] = df['Subscription_Type'].astype(str).str.title().str.strip()

        # Filter for valid types
        df_clean = df[df['Subscription_Type'].isin(['New', 'Renewed', 'Upgraded']) & df['Date'].notna()].copy()

        # Run Prediction
        result = get_xgboost_revenue_prediction(df_clean, days)

        if not result:
            return "€0.00", "€0.00", "€0.00", "€0.00", go.Figure()

        sums, dates, preds, hist = result['sums'], result['dates'], result['preds'], result['history']

        # Unpack predictions tuple
        p_total, p_new, p_ren, p_upg = preds

        fig = go.Figure()

        # ---------------------------------------------------------
        # 1. HISTORICAL DATA (ACTUAL) - Single Line, Multi-Hover
        # ---------------------------------------------------------
        # Build the HTML string for the hover tooltip
        hist_hover_text = [
            f"<b>Date:</b> {d.strftime('%Y-%m-%d')}<br>" +
            f"<b>Total:</b> €{t:,.2f}<br>" +
            f"----------------<br>" +
            f"New: €{n:,.2f}<br>" +
            f"Renewed: €{r:,.2f}<br>" +
            f"Upgraded: €{u:,.2f}"
            for d, t, n, r, u in zip(hist['Date'], hist['Total'], hist['New'], hist['Renewed'], hist['Upgraded'])
        ]

        fig.add_trace(go.Scatter(
            x=hist['Date'],
            y=hist['Total'],
            mode='lines',
            name="Total Revenue (Actual)",
            line=dict(color='#0d6efd', width=3),
            text=hist_hover_text,
            hovertemplate='%{text}<extra></extra>'  # <extra></extra> hides the secondary box
        ))

        # ---------------------------------------------------------
        # 2. FUTURE DATA (PREDICTED) - Single Line, Multi-Hover
        # ---------------------------------------------------------
        pred_hover_text = [
            f"<b>Date:</b> {d.strftime('%Y-%m-%d')}<br>" +
            f"<b>Total (Pred):</b> €{t:,.2f}<br>" +
            f"----------------<br>" +
            f"New: €{n:,.2f}<br>" +
            f"Renewed: €{r:,.2f}<br>" +
            f"Upgraded: €{u:,.2f}"
            for d, t, n, r, u in zip(dates, p_total, p_new, p_ren, p_upg)
        ]

        fig.add_trace(go.Scatter(
            x=dates,
            y=p_total,
            mode='lines',
            name="Total Revenue (Predicted)",
            line=dict(color='#dc3545', width=3, dash='dash'),
            text=pred_hover_text,
            hovertemplate='%{text}<extra></extra>'
        ))

        # ---------------------------------------------------------
        # 3. CONNECTOR LINE
        # ---------------------------------------------------------
        if len(p_total) > 0:
            fig.add_trace(go.Scatter(
                x=[hist['Date'].iloc[-1], dates[0]],
                y=[hist['Total'].iloc[-1], p_total[0]],
                mode='lines',
                showlegend=False,
                line=dict(color='#dc3545', width=3, dash='dash'),
                hoverinfo='skip'
            ))

        fig.update_layout(
            title="Revenue Forecast (XGBoost)",
            template="plotly_white",
            hovermode="x unified",
            yaxis_title="Revenue (€)",
            xaxis_title="Date"
        )

        return f"€{sums[0]:,.2f}", f"€{sums[1]:,.2f}", f"€{sums[2]:,.2f}", f"€{sums[3]:,.2f}", fig