import dash
from dash import html, dcc, callback, Input, Output, State
import dash_bootstrap_components as dbc
import pandas as pd

# --- IMPORT DATA LOADER ---
from Data.get_localsqldata import load_data

# --- IMPORT PAGES ---
# (Ensure you have saved the other page files in subscription_pages/)
from subscription_pages.daily_overview import layout as page1_layout, register_callbacks as register_page1_callbacks
from subscription_pages.monthly_overview import layout as page2_layout, register_callbacks as register_page2_callbacks
from subscription_pages.pie_chart import layout as page3_layout, register_callbacks as register_page3_callbacks
from subscription_pages.daily_revenue_bar_chart import layout as page4_layout, register_callbacks as register_page4_callbacks
from subscription_pages.monthly_revenue_bar_chart import layout as page5_layout, register_callbacks as register_page5_callbacks
from subscription_pages.daily_revenue_comparison import layout as page6_layout, register_callbacks as register_page6_callbacks
from subscription_pages.monthly_revenue_comparison import layout as page7_layout, register_callbacks as register_page7_callbacks
from subscription_pages.package_analysis import layout as page8_layout, register_callbacks as register_page8_callbacks

# AI Pages
from subscription_pages.prophet_forecast import prophet_layout, register_prophet_callbacks
from subscription_pages.prophet_employee_forecast import prophet_employee_layout, register_prophet_employee_callbacks
from subscription_pages.subscription_pre import churn_forecast_layout, register_churn_callbacks
from subscription_pages.xgboost_revenue_forecast import xgboost_revenue_layout, register_xgboost_revenue_callbacks

# --- APP SETUP ---
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP, dbc.icons.FONT_AWESOME], suppress_callback_exceptions=True)
server = app.server

# --- LOAD DATA ---
df = load_data()
initial_data = df.to_dict('records') if df is not None else []

# --- NAVBAR ---
navbar = dbc.Navbar(
    dbc.Container([
        html.A(dbc.Row([dbc.Col(html.I(className="fas fa-chart-line fa-lg me-2")), dbc.Col(dbc.NavbarBrand("Employer Dashboard"))], align="center"), href="/"),
        dbc.NavbarToggler(id="navbar-toggler"),
        dbc.Collapse(
            dbc.Nav([
                dbc.NavItem(dbc.NavLink("Daily Overview", href="/page-1")),
                dbc.NavItem(dbc.NavLink("Monthly Overview", href="/page-2")),
                dbc.NavItem(dbc.NavLink("Pie Chart", href="/page-3")),
                dbc.NavItem(dbc.NavLink("Package Analysis", href="/page-8")),
                dbc.DropdownMenu([
                    dbc.DropdownMenuItem("Revenue (Prophet)", href="/forecast-prophet"),
                    dbc.DropdownMenuItem("Revenue (XGBoost)", href="/forecast-xgboost"),
                    dbc.DropdownMenuItem(divider=True),
                    dbc.DropdownMenuItem("Employee (XGBoost)", href="/forecast-churn-xgb"),
                    dbc.DropdownMenuItem("Employee (Prophet)", href="/forecast-employee-prophet"),
                ], nav=True, in_navbar=True, label="AI Forecasts"),
                dbc.DropdownMenu([
                    dbc.DropdownMenuItem("Daily Revenue", href="/page-4"),
                    dbc.DropdownMenuItem("Monthly Revenue", href="/page-5"),
                    dbc.DropdownMenuItem("Daily Comparison", href="/page-6"),
                    dbc.DropdownMenuItem("Monthly Comparison", href="/page-7"),
                ], nav=True, in_navbar=True, label="Revenue Analytics"),
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

# --- REGISTER CALLBACKS ---
register_page1_callbacks(app)
register_page2_callbacks(app)
register_page3_callbacks(app)
register_page4_callbacks(app)
register_page5_callbacks(app)
register_page6_callbacks(app)
register_page7_callbacks(app)
register_page8_callbacks(app)
register_prophet_callbacks(app)
register_prophet_employee_callbacks(app)
register_churn_callbacks(app)
register_xgboost_revenue_callbacks(app)

# --- ROUTING ---
@app.callback(Output('page-content', 'children'), Input('url', 'pathname'))
def display_page(pathname):
    if pathname == '/page-1': return page1_layout
    elif pathname == '/page-2': return page2_layout
    elif pathname == '/page-3': return page3_layout
    elif pathname == '/page-4': return page4_layout
    elif pathname == '/page-5': return page5_layout
    elif pathname == '/page-6': return page6_layout
    elif pathname == '/page-7': return page7_layout
    elif pathname == '/page-8': return page8_layout
    elif pathname == '/forecast-prophet': return prophet_layout
    elif pathname == '/forecast-xgboost': return xgboost_revenue_layout
    elif pathname == '/forecast-churn-xgb': return churn_forecast_layout
    elif pathname == '/forecast-employee-prophet': return prophet_employee_layout
    else: return page1_layout

@app.callback(Output("navbar-collapse", "is_open"), [Input("navbar-toggler", "n_clicks")], [State("navbar-collapse", "is_open")])
def toggle_navbar_collapse(n, is_open):
    if n: return not is_open
    return is_open

if __name__ == '__main__':
    app.run(debug=True, port=8050)