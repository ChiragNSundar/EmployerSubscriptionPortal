import pandas as pd
from sqlalchemy import create_engine
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
    local_conn_str = (
        f"mysql+pymysql://{local_config['user']}:{local_config['password']}"
        f"@{local_config['host']}:{local_config['port']}/{local_config['database']}"
    )

    try:
        print(f"🔄 Connecting to Local Database ({local_config['database']})...")
        local_engine = create_engine(local_conn_str)

        # Select all columns
        query = "SELECT * FROM graph_subscription where dateUTC IS NOT NULL;"
        df = pd.read_sql(query, con=local_engine)

        if df.empty:
            print("⚠️ Table 'graph_subscription' is empty.")
            return df

        # --- RENAME COLUMNS ---
        # Added the specific date columns to ensure they are mapped correctly if needed
        column_mapping = {
            'dateUTC': 'Date',
            'type': 'Subscription_Type',
            'companyName': 'Company',
            'country': 'Location',
            'currentPackageAmountEUR': 'Revenue',
            'userStatus': 'User_Status',
            'recruitMode': 'Recruit_Mode',
            'currentPackageName': 'Package_Name',
            'cancellationReason': 'Cancellation_Reason',
            'userID': 'User_ID',

            # Ensuring these are mapped if the SQL names differ, 
            # otherwise they pass through as-is if they match the keys below
            'customerCreatedTimeUTC': 'customerCreatedTimeUTC',
            'initialSubsStartDate': 'initialSubsStartDate',
            'lastPaymentReceivedOn': 'lastPaymentReceivedOn',
            'subscriptionCanceledAt': 'subscriptionCanceledAt'
        }

        # Apply the renaming
        df.rename(columns=column_mapping, inplace=True)

        print(f"✅ Success! Loaded {len(df)} rows.")
        return df

    except Exception as e:
        print(f"❌ Error fetching data from local SQL: {e}")
        return None


if __name__ == "__main__":
    df_result = load_data()
    if df_result is not None:
        print(df_result.info())