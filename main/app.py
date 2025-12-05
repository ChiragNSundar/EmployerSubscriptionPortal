# dashboard/app.py

import pandas as pd
import dash
from dash import html, dcc, callback, Input, Output, State
import dash_bootstrap_components as dbc

# --- IMPORT DATA LOADING ---
from Data.get_localsqldata import load_data

# --- IMPORT EXISTING PAGES ---
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
from subscription_pages.package_analysis import layout as page8_layout, \
    register_callbacks as register_page8_callbacks

# --- IMPORT AI FORECAST PAGES ---

# 1. Revenue Forecast (Random Forest - Original)
# from subscription_pages.forecast import layout as page_forecast_layout, \
#     register_callbacks as register_forecast_callbacks

# 2. Employee Volume Forecast (Random Forest)
from subscription_pages.subscription_pre import employee_forecast_layout as page_employee_layout, \
    register_employee_callbacks as register_employee_callbacks

# 3. Revenue Forecast (Prophet)
from subscription_pages.prophet_forecast import prophet_layout as page_prophet_layout, \
    register_prophet_callbacks as register_prophet_callbacks

# 4. Employee Volume Forecast (Prophet - NEW)
# Ensure you saved the previous code as 'prophet_employee_forecast.py'
from subscription_pages.prophet_employee_forecast import prophet_employee_layout as page_prophet_employee_layout, \
    register_prophet_employee_callbacks as register_prophet_employee_callbacks

# 5. Churn Forecast (Commented out)
# from subscription_pages.churn_forecast import churn_layout as page_churn_layout, \
#     register_churn_callbacks as register_churn_callbacks


# --- INITIALIZE APP ---
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP, dbc.icons.FONT_AWESOME],
    suppress_callback_exceptions=True,
    title="Employer Subscription Dashboard"
)

# --- FETCH DATA ON STARTUP ---
print("🚀 Loading data from Local SQL...")
try:
    df = load_data()

    if df is not None and not df.empty:
        # Handle Date Serialization
        if 'Date' in df.columns:
            df['Date'] = df['Date'].astype(str)

        for col in df.select_dtypes(include=['datetime64']).columns:
            df[col] = df[col].astype(str)

        initial_data = df.to_dict('records')
        print(f"✅ Data loaded successfully: {len(df)} rows.")
    else:
        initial_data = []
        print("⚠️ Data is empty or None.")

except Exception as e:
    print(f"❌ Error loading initial data: {e}")
    initial_data = []


# --- NAVBAR COMPONENT ---
def create_navbar():
    return dbc.Navbar(
        dbc.Container([
            # Brand / Logo
            html.A(
                dbc.Row([
                    dbc.Col(html.I(className="fas fa-chart-line fa-lg me-2", style={"color": "#00d2ff"})),
                    dbc.Col(dbc.NavbarBrand("Employer Subscription Dashboard", className="ms-2")),
                ], align="center", className="g-0"),
                href="/",
                style={"textDecoration": "none"},
            ),

            # Toggler
            dbc.NavbarToggler(id="navbar-toggler", n_clicks=0),

            # Collapsible Links
            dbc.Collapse(
                dbc.Nav([
                    dbc.NavItem(dbc.NavLink("Daily Overview", href="/page-1")),
                    dbc.NavItem(dbc.NavLink("Monthly Overview", href="/page-2")),
                    dbc.NavItem(dbc.NavLink("Pie Chart", href="/page-3")),
                    dbc.NavItem(dbc.NavLink("Package Analysis", href="/page-8")),

                    # --- UPDATED: AI FORECAST DROPDOWN ---
                    dbc.DropdownMenu(
                        children=[
                            # Revenue Section
                            # dbc.DropdownMenuItem("Revenue Forecast (Random Forest)", href="/page-forecast"),
                            dbc.DropdownMenuItem("Revenue Forecast (Prophet)", href="/page-forecast-prophet"),

                            dbc.DropdownMenuItem(divider=True),

                            # Employee Volume Section
                            dbc.DropdownMenuItem("Employee Volume (Random Forest)", href="/page-forecast-employee"),
                            dbc.DropdownMenuItem("Employee Volume (Prophet)", href="/page-forecast-employee-prophet"),
                            # NEW LINK

                            # dbc.DropdownMenuItem("Churn Analysis", href="/page-forecast-churn"),
                        ],
                        nav=True,
                        in_navbar=True,
                        label="AI Forecasts",
                    ),

                    # Revenue Analytics Dropdown
                    dbc.DropdownMenu(
                        children=[
                            dbc.DropdownMenuItem("Daily Revenue Bar", href="/page-4"),
                            dbc.DropdownMenuItem("Monthly Revenue Bar", href="/page-5"),
                            dbc.DropdownMenuItem(divider=True),
                            dbc.DropdownMenuItem("Daily Comparison", href="/page-6"),
                            dbc.DropdownMenuItem("Monthly Comparison", href="/page-7"),
                        ],
                        nav=True,
                        in_navbar=True,
                        label="Revenue Analytics",
                    ),
                ], className="ms-auto", navbar=True),
                id="navbar-collapse",
                navbar=True,
            ),
        ]),
        color="dark",
        dark=True,
        className="mb-4 sticky-top",
        expand="lg"
    )


# --- APP LAYOUT ---
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    dcc.Store(id='global-data-store', data=initial_data),

    # Navbar
    create_navbar(),

    # Page Content
    dbc.Container([
        html.Div(id='page-content')
    ], fluid=True)
])

# --- REGISTER PAGE CALLBACKS ---
register_page1_callbacks(app)
register_page2_callbacks(app)
register_page3_callbacks(app)
register_page4_callbacks(app)
register_page5_callbacks(app)
register_page6_callbacks(app)
register_page7_callbacks(app)
register_page8_callbacks(app)

# Register AI Forecast Callbacks
# register_forecast_callbacks(app)  # Revenue (Random Forest)
register_prophet_callbacks(app)  # Revenue (Prophet)
register_employee_callbacks(app)  # Employee Volume (Random Forest)
register_prophet_employee_callbacks(app)  # Employee Volume (Prophet) - NEW


# register_churn_callbacks(app)   # Churn


# --- NAVBAR TOGGLE CALLBACK ---
@callback(
    Output("navbar-collapse", "is_open"),
    [Input("navbar-toggler", "n_clicks")],
    [State("navbar-collapse", "is_open")],
)
def toggle_navbar_collapse(n, is_open):
    if n:
        return not is_open
    return is_open


# --- ROUTING CALLBACK ---
@callback(
    Output('page-content', 'children'),
    Input('url', 'pathname')
)
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

    # AI Forecast Pages
    # elif pathname == '/page-forecast':
    #     return page_forecast_layout
    elif pathname == '/page-forecast-prophet':
        return page_prophet_layout
    elif pathname == '/page-forecast-employee':
        return page_employee_layout
    elif pathname == '/page-forecast-employee-prophet':  # NEW ROUTE
        return page_prophet_employee_layout

    # elif pathname == '/page-forecast-churn':
    #     return page_churn_layout

    else:
        # Default page
        return page1_layout


if __name__ == '__main__':
    app.run(port=8050, debug=True)

            # , host='0.0.0.0')
