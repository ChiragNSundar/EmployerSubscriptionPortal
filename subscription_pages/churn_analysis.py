import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.preprocessing import LabelEncoder

# --- 1. LOAD DATA ---
# Assuming you use your existing function to get the dataframe
from Data.get_localsqldata import load_data

print("🚀 Loading Data...")
df = load_data()

if df is None or df.empty:
    print("❌ No data found.")
    exit()

# --- 2. DATA PREPROCESSING & FEATURE ENGINEERING ---

print("⚙️ Preprocessing Data...")

# A. Create the Target Variable (1 = Churned, 0 = Active)
# If 'subscriptionCanceledAt' has a date, they churned. If it is NaT (Null), they are active.
df['Is_Churned'] = df['subscriptionCanceledAt'].notnull().astype(int)

# B. Create "Tenure" (How many days have they been with us?)
# We use 'initialSubsStartDate'.
# If churned: Tenure = Canceled Date - Start Date
# If active:  Tenure = Today - Start Date
today = pd.Timestamp.now()
df['Tenure_Days'] = df.apply(
    lambda row: (row['subscriptionCanceledAt'] - row['initialSubsStartDate']).days
    if pd.notnull(row['subscriptionCanceledAt'])
    else (today - row['initialSubsStartDate']).days,
    axis=1
)

# Handle negative days (dirty data check)
df['Tenure_Days'] = df['Tenure_Days'].apply(lambda x: max(0, x))

# C. Select Useful Features
# We drop IDs, Emails, and Dates (since we extracted Tenure from dates)
features = [
    'Subscription_Type',
    'Location',
    'Recruit_Mode',
    'Package_Name',
    'convertedFromTrial',
    'lastAmountPaidEUR',
    'Tenure_Days'
]

X = df[features].copy()
y = df['Is_Churned']

# D. Handle Missing Values
# Fill numeric missing values with 0
X['lastAmountPaidEUR'] = X['lastAmountPaidEUR'].fillna(0)
# Fill categorical missing values with 'Unknown'
X['Recruit_Mode'] = X['Recruit_Mode'].fillna('Unknown')

# E. Encode Categorical Data (Convert Text to Numbers)
# Machine Learning models cannot read text like "Germany" or "Premium".
# We use LabelEncoder to turn them into numbers (0, 1, 2...).
label_encoders = {}
categorical_cols = ['Subscription_Type', 'Location', 'Recruit_Mode', 'Package_Name']

for col in categorical_cols:
    le = LabelEncoder()
    # Convert to string to ensure consistency
    X[col] = le.fit_transform(X[col].astype(str))
    label_encoders[col] = le # Save encoder if we need to reverse it later

# --- 3. TRAIN/TEST SPLIT ---
# 80% of data for Training, 20% for Testing
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

print(f"📊 Training on {len(X_train)} rows, Testing on {len(X_test)} rows...")

# --- 4. INITIALIZE AND TRAIN MODEL ---
# n_estimators=100: Build 100 decision trees
model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

print("✅ Model Trained Successfully!")

# --- 5. EVALUATE MODEL ---
# Make predictions on the test set
y_pred = model.predict(X_test)

# Calculate Accuracy
accuracy = accuracy_score(y_test, y_pred)
print(f"\n🎯 Model Accuracy: {accuracy * 100:.2f}%")

# Detailed Report
print("\n📝 Classification Report:")
print(classification_report(y_test, y_pred))

# --- 6. FEATURE IMPORTANCE (The "Why") ---
# This tells us which columns contributed most to the decision to churn
importances = model.feature_importances_
feature_names = X.columns
feature_importance_df = pd.DataFrame({'Feature': feature_names, 'Importance': importances})
feature_importance_df = feature_importance_df.sort_values(by='Importance', ascending=False)

print("\n🔍 Top Factors Driving Churn:")
print(feature_importance_df)