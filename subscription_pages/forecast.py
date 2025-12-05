# import pandas as pd
# import numpy as np
# import plotly.graph_objs as go
# from dash import html, dcc, Input, Output, State
# import dash_bootstrap_components as dbc
# from sklearn.ensemble import RandomForestRegressor
# import itertools
#
# # --- 1. LAYOUT DEFINITION ---
# layout = dbc.Container([
#     html.H3("AI Revenue Forecasting (RF + Outlier Removal)", className="my-4 text-center text-white"),
#
#     # --- KPI Cards Row ---
#     dbc.Row([
#         dbc.Col([
#             dbc.Card([
#                 dbc.CardBody([
#                     html.H6(id='card-total-title', children="Total Revenue Predicted",
#                             className="card-title text-muted"),
#                     html.H4(id='card-total-pred', children="€0.00", className="text-primary fw-bold")
#                 ])
#             ], className="shadow-sm mb-3")
#         ], width=6, md=3),
#         dbc.Col([
#             dbc.Card([
#                 dbc.CardBody([
#                     html.H6(id='card-new-title', children="New Revenue Predicted", className="card-title text-muted"),
#                     html.H4(id='card-new-pred', children="€0.00", className="text-success fw-bold")
#                 ])
#             ], className="shadow-sm mb-3")
#         ], width=6, md=3),
#         dbc.Col([
#             dbc.Card([
#                 dbc.CardBody([
#                     html.H6(id='card-renewed-title', children="Renewed Revenue Predicted",
#                             className="card-title text-muted"),
#                     html.H4(id='card-renewed-pred', children="€0.00", className="text-info fw-bold")
#                 ])
#             ], className="shadow-sm mb-3")
#         ], width=6, md=3),
#         dbc.Col([
#             dbc.Card([
#                 dbc.CardBody([
#                     html.H6(id='card-upgraded-title', children="Upgraded Revenue Predicted",
#                             className="card-title text-muted"),
#                     html.H4(id='card-upgraded-pred', children="€0.00", className="text-warning fw-bold")
#                 ])
#             ], className="shadow-sm mb-3")
#         ], width=6, md=3),
#     ], className="mb-2"),
#
#     # --- Controls Row ---
#     dbc.Row([
#         # --- COLUMN 1: DAYS INPUT ---
#         dbc.Col([
#             html.Label("Days to Predict:", className="fw-bold"),
#             dbc.Input(id='forecast-days', type='number', value=30, min=7, max=365, step=1)
#         ], width=12, md=6, style={'zIndex': '1000', 'position': 'relative'}),
#
#         # --- COLUMN 2: BUTTON ---
#         dbc.Col([
#             html.Br(),
#             dbc.Button("Generate Revenue Forecast", id='btn-run-forecast', color="primary", className="w-100")
#         ], width=12, md=6, style={'zIndex': '1000', 'position': 'relative'}),
#
#     ],
#         className="mb-4 glass-container",
#         style={'overflow': 'visible', 'position': 'relative', 'zIndex': '1000'}
#     ),
#
#     # --- GRAPH ROW ---
#     dbc.Row([
#         dbc.Col([
#             dbc.Card([
#                 dbc.CardBody([
#                     dcc.Loading(
#                         id="loading-forecast",
#                         type="default",
#                         children=dcc.Graph(id='forecast-graph', style={'height': '500px'})
#                     )
#                 ])
#             ],
#                 className="shadow-sm glass-container",
#                 style={'zIndex': '1', 'position': 'relative'}
#             )
#         ], width=12)
#     ])
# ], fluid=True)
#
#
# # --- HELPER FUNCTION: RANDOM FOREST (DATE ONLY + OUTLIER REMOVAL) ---
# def get_revenue_prediction(df_in, days_to_predict):
#     df = df_in.copy()
#
#     # 1. Clean Dates
#     df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
#     df = df.dropna(subset=['Date'])
#
#     if df.empty: return None
#
#     # ============================================================
#     # --- NEW STEP: REMOVE OUTLIERS (IQR Method) ---
#     # ============================================================
#     # We only apply this if we have enough data points (>20) to calculate stats
#     if len(df) > 20:
#         Q1 = df['Revenue'].quantile(0.25)
#         Q3 = df['Revenue'].quantile(0.75)
#         IQR = Q3 - Q1
#
#         # Define bounds (1.5 is the standard statistical multiplier)
#         lower_bound = Q1 - 1.5 * IQR
#         upper_bound = Q3 + 1.5 * IQR
#
#         # Filter the dataframe
#         # We keep rows where Revenue is within the bounds
#         df = df[(df['Revenue'] >= lower_bound) & (df['Revenue'] <= upper_bound)]
#
#     # 2. Group Data (Date + Type Only)
#     df_grouped = df.groupby(['Date', 'Subscription_Type'])['Revenue'].sum().reset_index()
#
#     # 3. Feature Engineering (Time Features)
#     df_grouped['day_of_week'] = df_grouped['Date'].dt.dayofweek
#     df_grouped['day_of_month'] = df_grouped['Date'].dt.day
#     df_grouped['month'] = df_grouped['Date'].dt.month
#
#     # Trend Index (Days since start)
#     min_date = df_grouped['Date'].min()
#     df_grouped['trend_index'] = (df_grouped['Date'] - min_date).dt.days
#
#     # 4. One-Hot Encoding
#     df_encoded = pd.get_dummies(df_grouped, columns=['Subscription_Type'], drop_first=False)
#
#     # Define X (Features) and y (Target)
#     feature_cols = [c for c in df_encoded.columns if c not in ['Date', 'Revenue']]
#     X = df_encoded[feature_cols]
#     y = df_encoded['Revenue']
#
#     # 5. Train Model (RANDOM FOREST)
#     if len(df_encoded) < 10: return None
#
#     rf_model = RandomForestRegressor(
#         n_estimators=200,
#         random_state=42,
#         n_jobs=-1
#     )
#     rf_model.fit(X, y)
#
#     # 6. Prepare Future Data
#     last_date = df_grouped['Date'].max()
#     future_dates = [last_date + pd.Timedelta(days=x) for x in range(1, int(days_to_predict) + 1)]
#     unique_types = df_grouped['Subscription_Type'].unique()
#
#     # Create Cartesian Product (Date x Type)
#     future_combinations = list(itertools.product(future_dates, unique_types))
#     future_df = pd.DataFrame(future_combinations, columns=['Date', 'Subscription_Type'])
#
#     # Add Time Features to Future
#     future_df['day_of_week'] = future_df['Date'].dt.dayofweek
#     future_df['day_of_month'] = future_df['Date'].dt.day
#     future_df['month'] = future_df['Date'].dt.month
#     future_df['trend_index'] = (future_df['Date'] - min_date).dt.days
#
#     # One-Hot Encode Future Data
#     future_encoded = pd.get_dummies(future_df, columns=['Subscription_Type'], drop_first=False)
#
#     # --- ALIGN COLUMNS ---
#     future_X = future_encoded.reindex(columns=feature_cols, fill_value=0)
#
#     # 7. Predict
#     predictions = rf_model.predict(future_X)
#     future_df['Predicted_Revenue'] = np.maximum(predictions, 0)
#
#     # 8. Aggregate Results
#     final_forecast = future_df.groupby(['Date', 'Subscription_Type'])['Predicted_Revenue'].sum().reset_index()
#     forecast_pivot = final_forecast.pivot(index='Date', columns='Subscription_Type', values='Predicted_Revenue').fillna(
#         0)
#
#     for col in ['new', 'renewed', 'upgraded']:
#         if col not in forecast_pivot.columns: forecast_pivot[col] = 0
#
#     preds_new = forecast_pivot['new'].values
#     preds_renewed = forecast_pivot['renewed'].values
#     preds_upgraded = forecast_pivot['upgraded'].values
#     preds_total = preds_new + preds_renewed + preds_upgraded
#
#     graph_dates = forecast_pivot.index
#
#     # Prepare History Data
#     hist_grouped = df.groupby([pd.Grouper(key='Date', freq='D'), 'Subscription_Type'])['Revenue'].sum().reset_index()
#     hist_pivot = hist_grouped.pivot(index='Date', columns='Subscription_Type', values='Revenue').fillna(0)
#     for col in ['new', 'renewed', 'upgraded']:
#         if col not in hist_pivot.columns: hist_pivot[col] = 0
#
#     hist_pivot['total'] = hist_pivot['new'] + hist_pivot['renewed'] + hist_pivot['upgraded']
#     hist_df = hist_pivot.reset_index()
#
#     return {
#         'sums': (sum(preds_total), sum(preds_new), sum(preds_renewed), sum(preds_upgraded)),
#         'dates': graph_dates,
#         'preds': (preds_total, preds_new, preds_renewed, preds_upgraded),
#         'history': hist_df
#     }
#
#
# # --- 2. CALLBACK REGISTRATION ---
# def register_callbacks(app):
#     @app.callback(
#         [Output('card-total-pred', 'children'),
#          Output('card-new-pred', 'children'),
#          Output('card-renewed-pred', 'children'),
#          Output('card-upgraded-pred', 'children'),
#          Output('forecast-graph', 'figure'),
#          Output('card-total-title', 'children'),
#          Output('card-new-title', 'children'),
#          Output('card-renewed-title', 'children'),
#          Output('card-upgraded-title', 'children')],
#         [Input('btn-run-forecast', 'n_clicks')],
#         [State('global-data-store', 'data'),
#          State('forecast-days', 'value')]
#     )
#     def update_forecast(n_clicks, data, days):
#         empty_res = ("-", "-", "-", "-", go.Figure().update_layout(title="No Data"),
#                      "Total Revenue", "New Revenue", "Renewed Revenue", "Upgraded Revenue")
#
#         if not data: return empty_res
#         if n_clicks is None:
#             return "€0.00", "€0.00", "€0.00", "€0.00", go.Figure().update_layout(
#                 title="Click 'Generate Revenue Forecast' to see predictions",
#                 xaxis={'visible': False}, yaxis={'visible': False}
#             ), "Total Revenue", "New Revenue", "Renewed Revenue", "Upgraded Revenue"
#
#         df = pd.DataFrame(data)
#
#         # ============================================================
#         # 1. APPLY COLUMN MAPPING
#         # ============================================================
#         column_mapping = {
#             'dateUTC': 'Date',
#             'type': 'Subscription_Type',
#             'companyName': 'Company',
#             'country': 'Location',
#             'currentPackageAmountEUR': 'Revenue',
#             'userStatus': 'User_Status',
#             'recruitMode': 'Recruit_Mode',
#             'currentPackageName': 'Package_Name',
#             'cancellationReason': 'Cancellation_Reason',
#             'userID': 'User_ID'
#         }
#
#         df = df.rename(columns=column_mapping)
#
#         # ============================================================
#         # 2. DATA CLEANING
#         # ============================================================
#         required_cols = ['Date', 'Revenue', 'Subscription_Type']
#         if not all(col in df.columns for col in required_cols):
#             return empty_res
#
#         df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
#         df['Revenue'] = pd.to_numeric(df['Revenue'], errors='coerce').fillna(0)
#         df['Subscription_Type'] = df['Subscription_Type'].astype(str).str.lower().str.strip()
#
#         valid_types = ['new', 'renewed', 'upgraded']
#         mask_type = df['Subscription_Type'].isin(valid_types)
#         mask_date = df['Date'].notna()
#
#         df_clean = df[mask_type & mask_date].copy()
#
#         # ============================================================
#         # 3. RUN PREDICTION (DATE ONLY + OUTLIER REMOVAL)
#         # ============================================================
#
#         result = get_revenue_prediction(df_clean, days)
#
#         if not result:
#             return empty_res
#
#         (sum_total, sum_new, sum_renewed, sum_upgraded) = result['sums']
#         f_dates = result['dates']
#         (p_total, p_new, p_renewed, p_upgraded) = result['preds']
#         hist_df = result['history']
#
#         def fmt(val):
#             return f"€{val:,.2f}"
#
#         # ============================================================
#         # 4. GENERATE GRAPH
#         # ============================================================
#         fig = go.Figure()
#
#         def add_traces(hist_col, pred_vals, name, color, is_total=False):
#             opacity = 1 if is_total else 0
#             show_legend = True if is_total else False
#             pred_color = "#dc3545" if is_total else color
#
#             # History
#             fig.add_trace(go.Scatter(
#                 x=hist_df['Date'],
#                 y=hist_df[hist_col],
#                 mode='lines',
#                 name=f"{name} (Actual)",
#                 line=dict(color=color, width=3),
#                 opacity=opacity,
#                 showlegend=show_legend,
#                 hoverinfo='x+y+name'
#             ))
#
#             # Prediction
#             fig.add_trace(go.Scatter(
#                 x=f_dates,
#                 y=pred_vals,
#                 mode='lines',
#                 name=f"{name} (Predicted)",
#                 line=dict(color=pred_color, width=3, dash='dash'),
#                 opacity=opacity,
#                 showlegend=show_legend,
#                 hoverinfo='x+y+name'
#             ))
#
#             # Connector
#             if len(pred_vals) > 0:
#                 fig.add_trace(go.Scatter(
#                     x=[hist_df['Date'].iloc[-1], f_dates[0]],
#                     y=[hist_df[hist_col].iloc[-1], pred_vals[0]],
#                     mode='lines',
#                     showlegend=False,
#                     line=dict(color=pred_color, width=3, dash='dash'),
#                     opacity=opacity,
#                     hoverinfo='skip'
#                 ))
#
#         add_traces('total', p_total, "Total", "#0d6efd", is_total=True)
#         add_traces('new', p_new, "New", "#198754", is_total=False)
#         add_traces('renewed', p_renewed, "Renewed", "#0dcaf0", is_total=False)
#         add_traces('upgraded', p_upgraded, "Upgraded", "#ffc107", is_total=False)
#
#         fig.update_layout(
#             title=f"Revenue Forecast ({days} Days) - Outliers Removed (IQR Method)",
#             xaxis_title="Date",
#             yaxis_title="Revenue (€)",
#             template="plotly_white",
#             hovermode="x unified",
#             legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
#         )
#
#         title_suffix = f"(Next {days} Days)"
#
#         return (fmt(sum_total), fmt(sum_new), fmt(sum_renewed), fmt(sum_upgraded), fig,
#                 f"Total Revenue {title_suffix}",
#                 f"New Revenue {title_suffix}",
#                 f"Renewed Revenue {title_suffix}",
#                 f"Upgraded Revenue {title_suffix}")