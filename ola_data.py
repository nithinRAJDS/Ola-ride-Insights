"""Pure-pandas data layer for the OLA dashboard (no Streamlit dependency, so it is unit-testable)."""
import pandas as pd

VEHICLE_ORDER = ["Prime Sedan", "Prime SUV", "Prime Plus", "Mini", "Auto", "Bike", "E-Bike"]
STATUS_ORDER = ["Success", "Canceled by Driver", "Canceled by Customer", "Driver Not Found"]


def load(path="ola_cleaned.csv") -> pd.DataFrame:
    # keep the literal string "N/A" (not-applicable) instead of letting pandas turn it into NaN
    df = pd.read_csv(path, parse_dates=["Date", "Day"], keep_default_na=False, na_values=[""])
    df["Weekday"] = pd.Categorical(
        df["Weekday"],
        ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
        ordered=True,
    )
    return df


def apply_filters(df, vehicles, statuses, payments, date_range):
    m = df["Vehicle_Type"].isin(vehicles) & df["Booking_Status"].isin(statuses)
    if payments is not None:
        # payment method only exists for completed rides ("N/A" otherwise)
        m &= df["Payment_Method"].isin(payments) | (df["Payment_Method"] == "N/A")
    if date_range and len(date_range) == 2:
        m &= (df["Day"] >= pd.Timestamp(date_range[0])) & (df["Day"] <= pd.Timestamp(date_range[1]))
    return df[m]


def kpis(df):
    s = df[df.Is_Success == 1]
    n = len(df)
    return {
        "bookings": n,
        "success_rate": (len(s) / n) if n else 0.0,
        "total_value": df.Booking_Value.sum(),
        "success_value": s.Booking_Value.sum(),
        "lost_value": df.loc[df.Is_Success == 0, "Booking_Value"].sum(),
        "avg_distance": s.Ride_Distance.mean() if len(s) else 0.0,
        "avg_value": s.Booking_Value.mean() if len(s) else 0.0,
        "driver_rating": s.Driver_Ratings.mean() if len(s) else float("nan"),
        "customer_rating": s.Customer_Rating.mean() if len(s) else float("nan"),
    }


def vehicle_table(df):
    s = df[df.Is_Success == 1]
    t = pd.DataFrame({
        "Total Booking Value": df.groupby("Vehicle_Type").Booking_Value.sum(),
        "Success Booking Value": s.groupby("Vehicle_Type").Booking_Value.sum(),
        "Avg Distance (km)": s.groupby("Vehicle_Type").Ride_Distance.mean(),
        "Total Distance (km)": s.groupby("Vehicle_Type").Ride_Distance.sum(),
        "Success Rate": df.groupby("Vehicle_Type").Is_Success.mean(),
        "Avg Driver Rating": s.groupby("Vehicle_Type").Driver_Ratings.mean(),
        "Avg Customer Rating": s.groupby("Vehicle_Type").Customer_Rating.mean(),
    })
    return t.reindex([v for v in VEHICLE_ORDER if v in t.index])


def status_counts(df):
    return df.Booking_Status.value_counts().reindex(STATUS_ORDER).dropna().rename_axis("Status").reset_index(name="Bookings")


def daily(df):
    s = df[df.Is_Success == 1]
    d = df.groupby("Day").size().rename("Bookings").to_frame()
    d["Revenue"] = s.groupby("Day").Booking_Value.sum()
    return d.fillna(0).reset_index()


def hourly(df):
    return df.groupby("Hour").agg(Bookings=("Booking_ID", "count"), Success_Rate=("Is_Success", "mean")).reset_index()


def payment_revenue(df):
    s = df[df.Is_Success == 1]
    return s.groupby("Payment_Method").Booking_Value.sum().sort_values(ascending=False).rename("Revenue").reset_index()


def top_locations(df, n=10):
    s = df[df.Is_Success == 1]
    return s.groupby("Pickup_Location").Booking_Value.sum().sort_values(ascending=False).head(n).rename("Revenue").reset_index()


def cancel_reasons(df, who):
    status, col = {
        "Customer": ("Canceled by Customer", "Cancel_Reason_Customer"),
        "Driver": ("Canceled by Driver", "Cancel_Reason_Driver"),
    }[who]
    return df[df.Booking_Status == status][col].value_counts().rename_axis("Reason").reset_index(name="Count")


def failure_by_vehicle(df):
    ct = pd.crosstab(df.Vehicle_Type, df.Booking_Status, normalize="index") * 100
    ct = ct.drop(columns="Success", errors="ignore").reindex([v for v in VEHICLE_ORDER if v in ct.index])
    return ct.reset_index().melt("Vehicle_Type", var_name="Status", value_name="Percent")


def ratings_distribution(df):
    s = df[df.Is_Success == 1]
    return s.Driver_Ratings.round(1).value_counts().sort_index().rename_axis("Rating").reset_index(name="Rides")
