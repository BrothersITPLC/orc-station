from datetime import datetime, timedelta


def calculate_weeks_in_month(year):
    # Dictionary to hold the number of weeks in each month
    weeks_in_month = {}

    # Number of days in each month
    days_in_month = [
        31,
        29,
        31,
        30,
        31,
        30,
        31,
        31,
        30,
        31,
        30,
        31,
    ]  # February is 29 for leap year

    # Month names for output
    month_names = [
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ]

    for month in range(1, 13):
        # Get the first day of the month
        start_date = datetime(year, month, 1)
        # Get the number of days in the month
        num_days = days_in_month[month - 1]
        # Get the last day of the month
        end_date = start_date + timedelta(days=num_days - 1)

        # Calculate the total number of weeks
        total_days = (end_date - start_date).days + 1  # +1 to include the last day
        # Determine the start and end of the week
        start_weekday = start_date.weekday()  # Monday is 0 and Sunday is 6
        end_weekday = end_date.weekday()

        # Total weeks can be calculated as follows
        weeks = (total_days + start_weekday + 6) // 7  # +6 to round up

        # Store the result
        weeks_in_month[month_names[month - 1]] = weeks

    return weeks_in_month


# Calculate weeks for the year 2024
weeks_in_2024 = calculate_weeks_in_month(2024)

# Display the result
for month, weeks in weeks_in_2024.items():
    print(f"{month}: {weeks} weeks")
