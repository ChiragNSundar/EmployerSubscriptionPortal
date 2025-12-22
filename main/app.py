import dash
from dash import html, dcc, callback, Input, Output, State
import dash_bootstrap_components as dbc
import pandas as pd
from Data.get_localsqldata import load_data

# ==============================================================================
# 1. IMPORT EXISTING PAGES
# ==============================================================================
from subscription_pages.daily_overview import layout as page1_layout, register_callbacks as register_page1_callbacks
from subscription_pages.monthly_overview import layout as page2_layout, register_callbacks as register_page2_callbacks
from subscription_pages.pie_chart import layout as page3_layout, register_callbacks as register_page3_callbacks
from subscription_pages.daily_revenue_bar_chart import layout as page4_layout, \
    register_callbacks as register_page4_callbacks
from subscription_pages.monthly_revenue_bar_chart import layout as page5_layout, \
    register_callbacks as register_page5_callbacks
from subscription_pages.daily_revenue_comparison import layout as page6_layout, \
    register_callbacks as register_page6_callbacks
from subscription_pages.monthly_revenue_comparison import layout as page7_layout, \
    register_callbacks as register_page7_callbacks
from subscription_pages.package_analysis import layout as page8_layout, register_callbacks as register_page8_callbacks

# ==============================================================================
# 2. IMPORT ANALYTICS PAGES (REVENUE, VOLUME, CANCEL, PAID)
# ==============================================================================

# Revenue
from subscription_pages.revenue_insights import layout as revenue_time_layout, \
    register_callbacks as register_revenue_time_callbacks
from subscription_pages.location_revenue_insights import layout as revenue_location_layout, \
    register_callbacks as register_revenue_location_callbacks

# Volume (General)
from subscription_pages.volume_time import layout as volume_time_layout, \
    register_callbacks as register_volume_time_callbacks
from subscription_pages.volume_location import layout as volume_location_layout, \
    register_callbacks as register_volume_location_callbacks

# Paid Subscriptions
from subscription_pages.paid_subs_insights import layout as paid_subs_layout, \
    register_callbacks as register_paid_subs_callbacks
from subscription_pages.location_paid_insights import layout as loc_paid_layout, \
    register_callbacks as register_loc_paid_callbacks

# User Retention & Conversion
from subscription_pages.user_retention import layout as retention_layout, \
    register_callbacks as register_retention_callbacks

from subscription_pages.Time_to_First_Subscription import layout as first_sub_layout, \
    register_callbacks as register_first_sub_callbacks

# --- NEW PAGE IMPORT (Subscription Duration) ---
from subscription_pages.subscription_duration import layout as duration_layout, \
    register_callbacks as register_duration_callbacks

# Cancellations
from subscription_pages.cancellation_insights import layout as cancellation_layout, \
    register_callbacks as register_cancellation_callbacks
from subscription_pages.location_cancellation_insights import layout as loc_cancel_layout, \
    register_callbacks as register_loc_cancel_callbacks

# ==============================================================================
# 3. IMPORT AI PAGES
# ==============================================================================
from subscription_pages.prophet_forecast import prophet_layout, register_prophet_callbacks
from subscription_pages.prophet_employee_forecast import prophet_employee_layout, register_prophet_employee_callbacks
from subscription_pages.subscription_pre import churn_forecast_layout, register_churn_callbacks
from subscription_pages.xgboost_revenue_forecast import xgboost_revenue_layout, register_xgboost_revenue_callbacks

# --- APP SETUP ---
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP, dbc.icons.FONT_AWESOME],
                suppress_callback_exceptions=True)
server = app.server

# --- LOAD DATA ---
df = load_data()

initial_data = df.to_dict('records') if df is not None else []

# --- NAVBAR ---
navbar = dbc.Navbar(
    dbc.Container([
        html.A(dbc.Row(
            [dbc.Col(html.I(className="fas fa-chart-line fa-lg me-2")), dbc.Col(dbc.NavbarBrand("Employer Dashboard"))],
            align="center"), href="/"),
        dbc.NavbarToggler(id="navbar-toggler"),
        dbc.Collapse(
            dbc.Nav([
                dbc.NavItem(dbc.NavLink("Daily Overview", href="/page-1")),
                dbc.NavItem(dbc.NavLink("Monthly Overview", href="/page-2")),
                dbc.NavItem(dbc.NavLink("Pie Chart", href="/page-3")),
                dbc.NavItem(dbc.NavLink("Package Analysis", href="/page-8")),

                # --- ANALYTICS DROPDOWN ---
                dbc.DropdownMenu([
                    # Revenue Section
                    dbc.DropdownMenuItem("💰 Revenue (Time)", href="/revenue-insights"),
                    dbc.DropdownMenuItem("🌍 Revenue (Location)", href="/location-revenue-insights"),
                    dbc.DropdownMenuItem(divider=True),

                    # Volume Section
                    dbc.DropdownMenuItem("📅 Volume (Time)", href="/volume-time"),
                    dbc.DropdownMenuItem("📍 Volume (Location)", href="/volume-location"),
                    dbc.DropdownMenuItem(divider=True),

                    # Paid Subs Section
                    dbc.DropdownMenuItem("💸 Paid Subs (Time)", href="/paid-subs-insights"),
                    dbc.DropdownMenuItem("🗺️ Paid Subs (Location)", href="/location-paid-insights"),

                    # Retention & Conversion Section
                    dbc.DropdownMenuItem("🔄 User Retention", href="/user-retention"),
                    dbc.DropdownMenuItem("⏱️ Time to First Sub", href="/time-to-first-sub"),
                    dbc.DropdownMenuItem("⏳ Sub Duration", href="/sub-duration"),  # <--- NEW LINK ADDED HERE
                    dbc.DropdownMenuItem(divider=True),

                    # Cancellation Section
                    dbc.DropdownMenuItem("📉 Cancel (Time)", href="/cancellation-insights"),
                    dbc.DropdownMenuItem("🚫 Cancel (Location)", href="/location-cancellation-insights"),

                    dbc.DropdownMenuItem(divider=True),
                    dbc.DropdownMenuItem("Daily Revenue Bar", href="/page-4"),
                    dbc.DropdownMenuItem("Monthly Revenue Bar", href="/page-5"),
                ], nav=True, in_navbar=True, label="Analytics"),

                # --- AI DROPDOWN ---
                dbc.DropdownMenu([
                    dbc.DropdownMenuItem("Revenue (Prophet)", href="/forecast-prophet"),
                    dbc.DropdownMenuItem("Revenue (XGBoost)", href="/forecast-xgboost"),
                    dbc.DropdownMenuItem(divider=True),
                    dbc.DropdownMenuItem("Churn (Prophet)", href="/forecast-churn-xgb"),
                    dbc.DropdownMenuItem("Employee (Prophet)", href="/forecast-employee-prophet"),
                ], nav=True, in_navbar=True, label="AI Forecasts"),

            ], className="ms-auto", navbar=True),
            id="navbar-collapse", navbar=True,
        ),
    ]), color="dark", dark=True, className="mb-4 sticky-top", expand="lg"
)

# --- LAYOUT ---
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    dcc.Store(id='global-data-store', data=initial_data),
    navbar,
    dbc.Container(html.Div(id='page-content'), fluid=True)
])

# ==============================================================================
# 4. REGISTER CALLBACKS
# ==============================================================================
# Standard Pages
register_page1_callbacks(app)
register_page2_callbacks(app)
register_page3_callbacks(app)
register_page4_callbacks(app)
register_page5_callbacks(app)
register_page6_callbacks(app)
register_page7_callbacks(app)
register_page8_callbacks(app)

# Analytics Callbacks
register_revenue_time_callbacks(app)
register_revenue_location_callbacks(app)
register_volume_time_callbacks(app)
register_volume_location_callbacks(app)
register_paid_subs_callbacks(app)
register_loc_paid_callbacks(app)
register_retention_callbacks(app)
register_first_sub_callbacks(app)
register_duration_callbacks(app)  # <--- NEW CALLBACK REGISTERED HERE
register_cancellation_callbacks(app)
register_loc_cancel_callbacks(app)

# AI Callbacks
register_prophet_callbacks(app)
register_prophet_employee_callbacks(app)
register_churn_callbacks(app)
register_xgboost_revenue_callbacks(app)


# ==============================================================================
# 5. ROUTING LOGIC
# ==============================================================================
@app.callback(Output('page-content', 'children'), Input('url', 'pathname'))
def display_page(pathname):
    # Standard Pages
    if pathname == '/page-1':
        return page1_layout
    elif pathname == '/page-2':
        return page2_layout
    elif pathname == '/page-3':
        return page3_layout
    elif pathname == '/page-4':
        return page4_layout
    elif pathname == '/page-5':
        return page5_layout
    elif pathname == '/page-6':
        return page6_layout
    elif pathname == '/page-7':
        return page7_layout
    elif pathname == '/page-8':
        return page8_layout

    # Analytic Routes
    elif pathname == '/revenue-insights':
        return revenue_time_layout
    elif pathname == '/location-revenue-insights':
        return revenue_location_layout
    elif pathname == '/volume-time':
        return volume_time_layout
    elif pathname == '/volume-location':
        return volume_location_layout

    # New Analytic Routes
    elif pathname == '/paid-subs-insights':
        return paid_subs_layout
    elif pathname == '/location-paid-insights':
        return loc_paid_layout
    elif pathname == '/user-retention':
        return retention_layout
    elif pathname == '/time-to-first-sub':
        return first_sub_layout
    elif pathname == '/sub-duration':  # <--- NEW ROUTE ADDED HERE
        return duration_layout
    elif pathname == '/cancellation-insights':
        return cancellation_layout
    elif pathname == '/location-cancellation-insights':
        return loc_cancel_layout

    # AI Routes
    elif pathname == '/forecast-prophet':
        return prophet_layout
    elif pathname == '/forecast-xgboost':
        return xgboost_revenue_layout
    elif pathname == '/forecast-churn-xgb':
        return churn_forecast_layout
    elif pathname == '/forecast-employee-prophet':
        return prophet_employee_layout

    else:
        return page1_layout


@app.callback(Output("navbar-collapse", "is_open"), [Input("navbar-toggler", "n_clicks")],
              [State("navbar-collapse", "is_open")])
def toggle_navbar_collapse(n, is_open):
    if n: return not is_open
    return is_open


# if __name__ == '__main__':
#     app.run(debug=True, port=8050)