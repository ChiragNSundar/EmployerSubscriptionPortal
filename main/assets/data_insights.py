from Data.get_localsqldata import load_data
import pandas as pd

df = load_data()

print(f"Data Shape: {df.shape}")

# --- DATA PREPARATION ---
# 1. Convert 'lastPaymentReceivedOn' to datetime objects
df['lastPaymentReceivedOn'] = pd.to_datetime(df['lastPaymentReceivedOn'], errors='coerce')

# 2. Convert 'lastAmountPaidEUR' to numeric
df['lastAmountPaidEUR'] = pd.to_numeric(df['lastAmountPaidEUR'], errors='coerce')

# 3. Drop rows where there is no payment date or amount
df_clean = df.dropna(subset=['lastPaymentReceivedOn', 'lastAmountPaidEUR']).copy()


# --- STEP 1: Calculate Total Revenue for Each Day ---
# We sum up specific days (e.g., all payments on 2025-09-15)
daily_sums = df_clean.groupby(df_clean['lastPaymentReceivedOn'].dt.date)['lastAmountPaidEUR'].sum().reset_index()
daily_sums.columns = ['Date', 'Daily_Revenue']

# Create 'Month' column for grouping
daily_sums['Month'] = pd.to_datetime(daily_sums['Date']).dt.to_period('M')


# --- STEP 2: Analyze Each Month ---
def get_monthly_details(group):
    # Find the day with the highest revenue in this month
    max_day_row = group.loc[group['Daily_Revenue'].idxmax()]

    # Find the day with the lowest revenue in this month
    min_day_row = group.loc[group['Daily_Revenue'].idxmin()]

    return pd.Series({
        'Min_Rev_Date': min_day_row['Date'],
        'Min_Rev_Amt': min_day_row['Daily_Revenue'],
        'Max_Rev_Date': max_day_row['Date'],
        'Max_Rev_Amt': max_day_row['Daily_Revenue'],
        'Total_Month_Revenue': group['Daily_Revenue'].sum(), # <--- Total Revenue of Each Month
        'Avg_Daily_Revenue': group['Daily_Revenue'].mean()
    })

# Apply the function
monthly_report = daily_sums.groupby('Month').apply(get_monthly_details, include_groups=False)

print("\n--- 📅 Detailed Monthly Report ---")
print(monthly_report)


# --- STEP 3: Global Statistics (Whole Data) ---

# 1. Total Revenue of Whole Data
total_revenue_overall = df_clean['lastAmountPaidEUR'].sum()

# 2. Average Revenue of Whole Data (Average Revenue per Active Day)
avg_daily_revenue_overall = daily_sums['Daily_Revenue'].mean()

# 3. Max/Min Days of Whole Data
max_day_date = daily_sums.loc[daily_sums['Daily_Revenue'].idxmax()]['Date']
max_day_value = daily_sums['Daily_Revenue'].max()

min_day_date = daily_sums.loc[daily_sums['Daily_Revenue'].idxmin()]['Date']
min_day_value = daily_sums['Daily_Revenue'].min()


# --- OUTPUT FINAL RESULTS ---
print("\n" + "="*40)
print("       📊 OVERALL DATA INSIGHTS       ")
print("="*40)
print(f"💰 Total Revenue (Whole Data):   €{total_revenue_overall:,.2f}")
print(f"⚖️  Avg Daily Revenue:           €{avg_daily_revenue_overall:,.2f}")
print("-" * 40)
print(f"📈 Best Day Ever:  {max_day_date} (Revenue: €{max_day_value:,.2f})")
print(f"📉 Worst Day Ever: {min_day_date} (Revenue: €{min_day_value:,.2f})")
print("="*40)