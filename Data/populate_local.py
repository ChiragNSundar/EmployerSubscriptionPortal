#pushes data retrieved from data_fetch.py to local sql hosted using xampp

import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
import pymysql

# --- IMPORT FROM FILE 1 ---
# This runs the logic in fetch_data.py to get the dataframe
from data_fetch import get_remote_data

# --- Local XAMPP Configuration ---
LOCAL_DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'employersubscriptionsdashboard',  # ✅ Your DB Name
    'port': 3306
}


def push_to_local_sql(df, local_config):
    """
    Truncates local table and inserts new data.
    """
    if df is None or df.empty:
        print("⚠️ No data to push to local database.")
        return

    # Construct Local Connection String
    local_conn_str = (
        f"mysql+pymysql://{local_config['user']}:{local_config['password']}"
        f"@{local_config['host']}:{local_config['port']}/{local_config['database']}"
    )

    try:
        local_engine = create_engine(local_conn_str)
        print(f"🔄 Connecting to Local Database ({local_config['database']})...")

        # 1. Clean Data (NaN -> NULL)
        df_clean = df.replace({np.nan: None})

        # 2. Insert Data
        with local_engine.connect() as connection:
            # A. Truncate (Clear old data)
            print("🧹 Clearing existing data in 'graph_subscription'...")
            connection.execute(text("TRUNCATE TABLE graph_subscription"))
            connection.commit()

            # B. Insert (Append new data)
            print("🔄 Inserting fresh data...")
            df_clean.to_sql(
                name='graph_subscription',
                con=connection,
                if_exists='append',
                index=False,
                chunksize=1000
            )

        print(f"✅ Success! Populated 'graph_subscription' with {len(df_clean)} rows.")

    except Exception as e:
        print(f"❌ Error pushing to local SQL: {e}")


# --- Execute ---
if __name__ == "__main__":
    print("🚀 Starting ETL Process...")

    # 1. Get Data from Remote (using File 1)
    remote_df = get_remote_data()

    # 2. Push Data to Local (using logic in this file)
    if remote_df is not None:
        push_to_local_sql(remote_df, LOCAL_DB_CONFIG)

    print("🏁 Process Finished.")

"""
CREATE TABLE graph_subscription (
    id INT NOT NULL PRIMARY KEY,
    userID INT,
    siteInstanceID INT,
    dateUTC DATETIME,
    type VARCHAR(50),
    userStatus VARCHAR(50),
    customerID VARCHAR(100),
    country VARCHAR(5),
    email VARCHAR(255),
    companyName VARCHAR(255),
    productID INT,
    recruitMode VARCHAR(50),
    customerCreatedTimeUTC DATETIME,
    currentPackageName VARCHAR(100),
    currentPackageAmountEUR DECIMAL(10, 2),
    currentSubsStatus VARCHAR(50),
    currentSubsStartDate DATETIME,
    currentSubsEndDate DATETIME,
    convertedFromTrial TINYINT, -- Uses 0 or 1
    totalRevenueEUR DECIMAL(10, 2),
    initialSubsStartDate DATETIME,
    lastPaymentReceivedOn DATETIME NULL,
    lastAmountPaidEUR DECIMAL(10, 2),
    subscriptionUpgradedAt DATETIME NULL,
    previousPackageName VARCHAR(100) NULL,
    previousProductID INT NULL,
    subscriptionCanceledAt DATETIME NULL,
    cancellationReason TEXT NULL, -- TEXT type to handle long JSON strings
    timeCreatedAtUTC DATETIME,
    timeUpdatedAtUTC DATETIME,
    timeModifiedDB DATETIME
);
"""