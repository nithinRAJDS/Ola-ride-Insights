import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

st.set_page_config(page_title="OLA Ride Analytics & SQL Console", layout="wide")

@st.cache_data
def load_data():
    df = pd.read_excel('/content/OLA_DataSet.xlsx')
    df['Hour'] = pd.to_datetime(df['Time'].astype(str), format='%H:%M:%S', errors='coerce').dt.hour
    # Align mapping for Is_Success helper column
    df['Is_Success'] = (df['Booking_Status'] == 'Success').astype(int)
    return df

try:
    df = load_data()
except Exception as e:
    st.error(f"Error loading dataset: {e}")
    st.stop()

st.title("🚖 OLA Rides Analytics Dashboard & SQL Console")
st.markdown("An interactive visual analytics engine exploring ride status, value metrics, feedback distributions, and integrated SQL recipes.")

# Sidebar Filters
st.sidebar.header("Filter Options")
vehicle_list = ["All"] + list(df["Vehicle_Type"].dropna().unique())
selected_vehicle = st.sidebar.selectbox("Select Vehicle Type", vehicle_list)

filtered_df = df if selected_vehicle == "All" else df[df["Vehicle_Type"] == selected_vehicle]

# 1. KPIs Section
st.header("1. Key Performance Indicators (KPIs)")
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total Bookings", f"{len(filtered_df):,}")
with col2:
    st.metric("Success Rate", f"{(filtered_df['Booking_Status'] == 'Success').mean() * 100:.2f}%")
with col3:
    st.metric("Average Ride Distance", f"{filtered_df['Ride_Distance'].mean():.2f} km")
with col4:
    st.metric("Total Booking Value", f"₹{filtered_df['Booking_Value'].sum():,}")

with st.expander("🔍 View Headline KPIs SQL Query"):
    st.code("""SELECT COUNT(*)                                                    AS total_bookings,
       SUM(CAST(Is_Success AS INT))                                AS completed_rides,
       CAST(100.0 * SUM(CAST(Is_Success AS INT)) / COUNT(*) AS DECIMAL(5,2)) AS success_rate_pct,
       SUM(Booking_Value)                                          AS total_booking_value,
       SUM(CASE WHEN Is_Success = 1 THEN Booking_Value END)        AS revenue,
       SUM(CASE WHEN Is_Success = 0 THEN Booking_Value END)        AS revenue_lost,
       CAST(AVG(CASE WHEN Is_Success = 1 THEN 1.0 * Booking_Value END) AS DECIMAL(8,2)) AS avg_fare,
       CAST(AVG(CASE WHEN Is_Success = 1 THEN 1.0 * Ride_Distance END) AS DECIMAL(6,2)) AS avg_distance_km
FROM dbo.ola_rides;""", language="sql")

st.markdown("---")

# 2. Demand & Outcomes Row
st.header("2. Demand Trends & Booking Outcomes")
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Booking Status Breakdown")
    status_counts = filtered_df['Booking_Status'].value_counts()
    fig, ax = plt.subplots(figsize=(6, 4))
    sns.barplot(x=status_counts.values, y=status_counts.index, palette="viridis", ax=ax)
    ax.set_xlabel("Count")
    st.pyplot(fig)

    with st.expander("🔍 View Booking Outcome Split SQL"):
        st.code("""SELECT booking_status,
       COUNT(*) AS bookings,
       CAST(100.0 * COUNT(*) / SUM(COUNT(*)) OVER () AS DECIMAL(5,2)) AS pct_of_bookings,
       SUM(booking_value) AS booking_value
FROM dbo.ola_rides
GROUP BY booking_status
ORDER BY bookings DESC;""", language="sql")

with col_right:
    st.subheader("Hourly Booking Value Trend")
    hourly_vals = filtered_df.groupby('Hour')['Booking_Value'].mean().reset_index()
    fig, ax = plt.subplots(figsize=(6, 4))
    sns.lineplot(data=hourly_vals, x='Hour', y='Booking_Value', marker='o', color='forestgreen', ax=ax)
    ax.set_ylabel("Average Booking Value")
    ax.grid(True, alpha=0.3)
    st.pyplot(fig)

    with st.expander("🔍 View Hourly Demand SQL"):
        st.code("""SELECT Booking_Hour,
       COUNT(*) AS bookings,
       CAST(100.0 * SUM(CAST(Is_Success AS INT)) / COUNT(*) AS DECIMAL(5,2)) AS success_rate_pct,
       RANK() OVER (ORDER BY 1.0 * SUM(CAST(Is_Success AS INT)) / COUNT(*) ASC) AS worst_hour_rank
FROM dbo.ola_rides
GROUP BY Booking_Hour
ORDER BY Booking_Hour;""", language="sql")

st.markdown("---")

# 3. Service Quality & Performance
st.header("3. Ratings & Service Speeds")
col_lower_left, col_lower_right = st.columns(2)

with col_lower_left:
    st.subheader("Driver vs. Customer Ratings")
    fig, ax = plt.subplots(figsize=(6, 4))
    sns.histplot(data=filtered_df, x='Customer_Rating', color='skyblue', label='Customer Rating', kde=True, bins=15, ax=ax, alpha=0.6)
    sns.histplot(data=filtered_df, x='Driver_Ratings', color='salmon', label='Driver Rating', kde=True, bins=15, ax=ax, alpha=0.6)
    ax.legend()
    ax.set_xlabel("Rating Value")
    st.pyplot(fig)

    with st.expander("🔍 View Rating Bands & TAT SQL"):
        st.code("""-- Ratings Segment
SELECT Vehicle_Type,
       SUM(CASE WHEN Driver_Ratings <  3.5 THEN 1 ELSE 0 END) AS low_lt_3_5,
       SUM(CASE WHEN Driver_Ratings >= 3.5 AND Driver_Ratings < 4.5 THEN 1 ELSE 0 END) AS mid_3_5_to_4_4,
       SUM(CASE WHEN Driver_Ratings >= 4.5 THEN 1 ELSE 0 END) AS high_4_5_plus,
       CAST(AVG(Driver_Ratings) AS DECIMAL(4,2)) AS avg_driver
FROM dbo.ola_rides WHERE Is_Success = 1
GROUP BY Vehicle_Type ORDER BY avg_driver DESC;

-- Service Speed (Turnaround Time)
SELECT Vehicle_Type, CAST(AVG(V_TAT) AS DECIMAL(6,1)) AS avg_V_TAT, CAST(AVG(C_TAT) AS DECIMAL(6,1)) AS avg_C_TAT
FROM dbo.ola_rides WHERE Is_Success = 1 GROUP BY Vehicle_Type ORDER BY avg_V_TAT;""", language="sql")

with col_lower_right:
    st.subheader("Vehicle Type Scorecard Summary")
    if not filtered_df.empty:
        v_scorecard = filtered_df.groupby('Vehicle_Type').agg(
            Total_Booking_Value=('Booking_Value', 'sum'),
            Success_Rate=('Is_Success', 'mean'),
            Avg_Distance=('Ride_Distance', 'mean'),
            Avg_Customer_Rating=('Customer_Rating', 'mean')
        ).reset_index()
        st.dataframe(v_scorecard.style.format({'Success_Rate': '{:.2%}', 'Avg_Distance': '{:.2f} km', 'Avg_Customer_Rating': '{:.2f}', 'Total_Booking_Value': '₹{:,}'}))
    else:
        st.write("No data available.")

    with st.expander("🔍 View Vehicle Scorecard SQL"):
        st.code("""SELECT Vehicle_Type,
       SUM(Booking_Value)                                          AS total_booking_value,
       SUM(CASE WHEN Is_Success = 1 THEN Booking_Value END)        AS success_booking_value,
       CAST(AVG(CASE WHEN Is_Success = 1 THEN 1.0 * Ride_Distance END) AS DECIMAL(6,2)) AS avg_distance_km,
       SUM(Ride_Distance)                                          AS total_distance_km,
       CAST(100.0 * SUM(CAST(Is_Success AS INT)) / COUNT(*) AS DECIMAL(5,2)) AS success_rate_pct,
       CAST(AVG(Driver_Ratings)  AS DECIMAL(4,2))                  AS avg_driver_rating,
       CAST(AVG(Customer_Rating) AS DECIMAL(4,2))                  AS avg_customer_rating
FROM dbo.ola_rides
GROUP BY Vehicle_Type
ORDER BY success_booking_value DESC;""", language="sql")

st.markdown("---")

# 4. Advanced Analytics & Operations Library
st.header("🗂️ Advanced Analytics & Query Repository")
st.markdown("Select any operation parameter below to view specialized SQL patterns for advanced insights.")

sql_section = st.selectbox("Choose Query Category", [
    "Cancellations & Failures Analysis",
    "Route, Revenue & Payment Mix",
    "Loyalty & Cohorts (One-time vs Repeat)",
    "Moving Averages & Demand Normalization"
])

if sql_section == "Cancellations & Failures Analysis":
    st.markdown("### Customer Cancellations & Driver-Induced Failure Patterns")
    st.code("""-- Customer cancellations reasons
SELECT Cancel_Reason_Customer AS reason, COUNT(*) AS cancellations,
       CAST(100.0*COUNT(*)/SUM(COUNT(*)) OVER () AS DECIMAL(5,2)) AS pct
FROM dbo.ola_rides WHERE Booking_Status = 'Canceled by Customer'
GROUP BY Cancel_Reason_Customer ORDER BY cancellations DESC;

-- Customer cancellations caused by driver behaviour
SELECT SUM(CASE WHEN Cancel_Reason_Customer IN ('Driver is not moving towards pickup location','Driver asked to cancel') THEN 1 ELSE 0 END) AS driver_induced,
       COUNT(*) AS all_customer_cancels,
       CAST(100.0*SUM(CASE WHEN Cancel_Reason_Customer IN ('Driver is not moving towards pickup location','Driver asked to cancel') THEN 1 ELSE 0 END)/COUNT(*) AS DECIMAL(5,2)) AS pct
FROM dbo.ola_rides WHERE Booking_Status = 'Canceled by Customer';""", language="sql")

elif sql_section == "Route, Revenue & Payment Mix":
    st.markdown("### Top Routes & Financial Mix")
    st.code("""-- Most popular routes (pickup -> drop) among completed rides
SELECT TOP 10 Pickup_Location, Drop_Location, COUNT(*) AS rides, SUM(Booking_Value) AS revenue
FROM dbo.ola_rides WHERE Is_Success = 1
GROUP BY Pickup_Location, Drop_Location ORDER BY rides DESC;

-- Revenue by payment method
SELECT Payment_Method, COUNT(*) AS rides, SUM(Booking_Value) AS revenue,
       CAST(100.0*SUM(Booking_Value)/SUM(SUM(Booking_Value)) OVER () AS DECIMAL(5,2)) AS pct_revenue
FROM dbo.ola_rides WHERE Is_Success = 1
GROUP BY Payment_Method ORDER BY revenue DESC;""", language="sql")

elif sql_section == "Loyalty & Cohorts (One-time vs Repeat)":
    st.markdown("### Repeat Users Revenue Analytics")
    st.code("""WITH c AS (SELECT Customer_ID, COUNT(*) AS bookings,
                  SUM(CASE WHEN Is_Success=1 THEN Booking_Value ELSE 0 END) AS revenue
           FROM dbo.ola_rides GROUP BY Customer_ID)
SELECT CASE WHEN bookings = 1 THEN 'One-time' ELSE 'Repeat (2+)' END AS segment,
       COUNT(*) AS customers, SUM(revenue) AS revenue,
       CAST(AVG(1.0*revenue) AS DECIMAL(10,2)) AS avg_revenue_per_customer
FROM c GROUP BY CASE WHEN bookings = 1 THEN 'One-time' ELSE 'Repeat (2+)' END;""", language="sql")

elif sql_section == "Moving Averages & Demand Normalization":
    st.markdown("### Demand Normalization & Rolling Performance Indicators")
    st.code("""-- Daily revenue with 7-day moving average
WITH d AS (
	SELECT Day_Key, COUNT(*) AS bookings,
	SUM(CASE WHEN is_success=1 THEN booking_value ELSE 0 END) AS revenue
FROM ola_rides GROUP BY Booking_Weekday)
SELECT Day_Key, bookings, revenue,
	CAST(AVG(1.0* revenue) OVER (ORDER BY day_key ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS DECIMAL(12,0)) AS revenue_7d_avg
FROM d ORDER BY Day_Key;""", language="sql")
