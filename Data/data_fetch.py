import pandas as pd
import pymysql
from sqlalchemy import create_engine
import pymongo
import os
from dotenv import load_dotenv

# --- 0. Load Environment Variables ---
load_dotenv()

# --- 1. MongoDB Connection Setup ---
MONGO_URI = os.getenv('MONGO_URI')
MONGO_DB_NAME = os.getenv('MONGO_DB_NAME')
MONGO_COLLECTION_NAME = os.getenv('MONGO_COLLECTION_NAME')


def get_config_from_mongo():
    if not MONGO_URI:
        print("❌ Error: MONGO_URI not found in .env file.")
        return None
    try:
        client = pymongo.MongoClient(MONGO_URI)
        db = client[MONGO_DB_NAME]
        collection = db[MONGO_COLLECTION_NAME]
        query = {"type": "db_connection_config"}
        document = collection.find_one(query)
        if document and 'connection_config' in document:
            print("✅ Configuration successfully retrieved from MongoDB.")
            return document['connection_config']
        else:
            print("⚠️ Document not found or missing 'connection_config' key.")
            return None
    except Exception as e:
        print(f"❌ Error connecting to MongoDB: {e}")
        return None


# --- 2. Define DB_CONFIG ---
mongo_config_data = get_config_from_mongo()

if mongo_config_data:
    DB_CONFIG = mongo_config_data
else:
    print("⚠️ Using local fallback configuration from .env.")
    DB_CONFIG = {
        'host': os.getenv('SQL_HOST'),
        'user': os.getenv('SQL_USER'),
        'password': os.getenv('SQL_PASSWORD'),
        'database': os.getenv('SQL_DATABASE'),
        'table_name': os.getenv('SQL_TABLE_NAME')
    }


# --- 3. Connect to Remote SQL and Fetch Data ---
def get_remote_data():
    """
    Connects to Remote SQL, fetches data, and returns the DataFrame.
    """
    config = DB_CONFIG

    if not config or not config.get('host'):
        print("❌ Operation aborted: Missing database configuration.")
        return None

    port = config.get('port', 3306)
    connection_string = (
        f"mysql+pymysql://{config['user']}:{config['password']}"
        f"@{config['host']}:{port}/{config['database']}"
    )

    try:
        engine = create_engine(connection_string)
        table_name = config.get('table_name')

        print(f"🔄 Connecting to Remote SQL Database ({config['host']})...")
        query = f"SELECT * FROM {table_name} WHERE `dateUTC` IS NOT NULL;"

        with engine.connect() as connection:
            df = pd.read_sql(query, connection)

        if not df.empty:
            print(f"✅ Data Fetched Successfully! ({len(df)} rows)")
            return df
        else:
            print("⚠️ The query returned an empty dataset.")
            return None

    except Exception as e:
        print(f"❌ Error fetching data from Remote SQL: {e}")
        return None


# Only run this if executing this file directly for testing
if __name__ == "__main__":
    df = get_remote_data()
    if df is not None:
        print(df.head())