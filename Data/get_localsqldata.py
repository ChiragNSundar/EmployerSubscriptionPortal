#fetches local sql data hosted on xampp sql server

import pandas as pd
from sqlalchemy import create_engine, text
import pymysql

# --- Local XAMPP Configuration ---
LOCAL_DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'employersubscriptionsdashboard',
    'port': 3306
}


def load_data(local_config=LOCAL_DB_CONFIG):
    """
    Connects to the local MySQL database, fetches data from 'graph_subscription',
    renames columns for clarity, and returns it as a Pandas DataFrame.
    """
    # 1. Construct Local Connection String
    local_conn_str = (
        f"mysql+pymysql://{local_config['user']}:{local_config['password']}"
        f"@{local_config['host']}:{local_config['port']}/{local_config['database']}"
    )

    try:
        print(f"🔄 Connecting to Local Database ({local_config['database']})...")

        # 2. Create Database Engine
        local_engine = create_engine(local_conn_str)

        # 3. Define the SQL Query
        query = "SELECT * FROM graph_subscription"

        # 4. Execute Query and Load into DataFrame
        df = pd.read_sql(query, con=local_engine)

        # 5. Check if data was retrieved
        if df.empty:
            print("⚠️ Connection successful, but the table 'graph_subscription' is empty.")
            return df

        # --- 6. RENAME COLUMNS ---
        # Mapping: {'Old_SQL_Name': 'New_Friendly_Name'}
        column_mapping = {
            'dateUTC': 'Date',  # Renamed for clarity
            'type': 'Subscription_Type',  # The column with New, Renewed, etc.
            'companyName': 'Company',
            'country': 'Location',
            'currentPackageAmountEUR': 'Revenue',
            'userStatus': 'User_Status',
            'recruitMode': 'Recruit_Mode',
            'currentPackageName': 'Package_Name',
            'cancellationReason': 'Cancellation_Reason',
            'userID': 'User_ID'
        }

        # Apply the renaming
        df.rename(columns=column_mapping, inplace=True)

        print(f"✅ Success! Loaded {len(df)} rows and renamed columns.")

        # Optional: Print new columns to verify
        # print("New Columns:", df.columns.tolist())

        return df

    except Exception as e:
        print(f"❌ Error fetching data from local SQL: {e}")
        return None

"""
# --- Execute for Testing ---
if __name__ == "__main__":
    df_result = load_data()
    if df_result is not None and not df_result.empty:
        print(df_result.head())
        print(df_result.info())
"""
