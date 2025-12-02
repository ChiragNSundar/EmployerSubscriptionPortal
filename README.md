pip install -r requirements.txt

.env should contain the following:
MONGO_URI=mongodblink
MONGO_DB_NAME=dbname
MONGO_COLLECTION_NAME=tablename

# Fallback SQL Configuration (Used if Mongo fails)
SQL_HOST=""
SQL_USER=""
SQL_PASSWORD=" "
SQL_DATABASE=""
SQL_TABLE_NAME=""