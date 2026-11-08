# OLA Ride Analytics – Streamlit app

    pip install -r requirements.txt
    streamlit run app.py

Files: `app.py` (UI), `ola_data.py` (pandas logic), `ola_cleaned.csv` (cleaned data, 103,024 rows).
Tabs mirror the dashboard deck: Overall, Vehicle Type, Revenue, Cancellation, Ratings, Data.
Sidebar filters: vehicle type, booking status, payment method, date range.

## Cleaning applied (July sheet → ola_cleaned.csv)
- No duplicate rows or Booking_IDs; 31 days (1–31 Jul 2024).
- Blank cells are structural, not missing data: ratings, TAT, payment method exist only for completed rides; cancellation reasons only for the matching status. Blanks were replaced with "N/A" in categorical columns and left empty in numeric ones.
- `eBike` renamed `E-Bike`; image-URL column dropped; added Day, Hour, Weekday, Week, Is_Success.
- Cancelled bookings keep their quoted Booking_Value, so "Total" vs "Success" booking value differ (₹5.65 Cr vs ₹3.51 Cr).

## Power BI build notes
Import `ola_cleaned.csv`. Core DAX measures:

    Total Bookings = COUNTROWS(ola)
    Success Bookings = CALCULATE([Total Bookings], ola[Booking_Status]="Success")
    Success Rate = DIVIDE([Success Bookings],[Total Bookings])
    Total Booking Value = SUM(ola[Booking_Value])
    Success Booking Value = CALCULATE([Total Booking Value], ola[Booking_Status]="Success")
    Lost Value = [Total Booking Value] - [Success Booking Value]
    Avg Distance = CALCULATE(AVERAGE(ola[Ride_Distance]), ola[Booking_Status]="Success")
    Total Distance = SUM(ola[Ride_Distance])
    Avg Driver Rating = CALCULATE(AVERAGE(ola[Driver_Ratings]), ola[Booking_Status]="Success")
    Avg Customer Rating = CALCULATE(AVERAGE(ola[Customer_Rating]), ola[Booking_Status]="Success")
    Cancel Rate = DIVIDE([Total Bookings]-[Success Bookings],[Total Bookings])
