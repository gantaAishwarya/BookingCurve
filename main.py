from matplotlib import pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
from datetime import datetime, timedelta
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import calendar

def read_data(file_path):
    """Read data from CSV file and return a DataFrame."""
    data = pd.read_csv(file_path)
    return data

def convert_to_datetime(df, columns):
    """Convert specified columns to datetime in the DataFrame."""
    df[columns] = df[columns].apply(pd.to_datetime)
    return df

def preprocessing(data):
    # Convert date columns to datetime
    date_columns = ['NIGHT_OF_STAY', 'DATE_LAST_MODIFIED', 'DATE_OF_RESERVATION', 'CANCELLATION_DATE', 'START_DATE_OF_STAY', 'END_DATE_OF_STAY']
    hotel_data = convert_to_datetime(data, date_columns)

    # Handling missing values in DATE_OF_RESERVATION
    hotel_data = hotel_data.dropna(subset=['DATE_OF_RESERVATION'])
    
    #TODO: Handle outliers in data
    #TODO: Based on requirements can handle other missing data and outliers
    return hotel_data

def days_in_month(year, month):
    #Calculating number of days in provided month for respective year
    return calendar.monthrange(year, month)[1]

def month_name_from_number(month):
    #Returning month name of the give month number
    return calendar.month_name[month]

def calculate_occupied_rooms(hotel_data,target_day,days_limit):
    """Calculating number of occupied rooms for respective day"""

    # Filter night stay data for the given day and reservation received between given day and days_limit (default:100) days leading up to it
    filtered_data_day = hotel_data[
    (hotel_data['NIGHT_OF_STAY'].dt.date == target_day.date()) &
    ((hotel_data['DATE_OF_RESERVATION'] >= target_day - timedelta(days=days_limit)) & (hotel_data['DATE_OF_RESERVATION'] <= target_day))]


    # Separate reserved and cancelled room data
    reserved_data = filtered_data_day[filtered_data_day['RPG_STATUS'] == 1]
    cancelled_data = filtered_data_day[filtered_data_day['RPG_STATUS'] == 2]

    # Remove duplicates for reservation data caused due to updating
    filtered_data_booked = reserved_data.groupby('DATE_OF_RESERVATION')['ROOM_RESERVATION_ID'].nunique().reset_index(name='RESERVATION_COUNT')

    # Calculate number of cancellations per day
    number_of_cancellation_days = cancelled_data.groupby('CANCELLATION_DATE').size().reset_index(name='CANCELLATION_COUNT')

    # Merge reservation and cancellation data
    merged_data = pd.merge(filtered_data_booked, number_of_cancellation_days, how='left', left_on='DATE_OF_RESERVATION', right_on='CANCELLATION_DATE')
    
    # Fill NaN values with 0 for dates with reservations but no cancellations
    merged_data['CANCELLATION_COUNT'].fillna(0, inplace=True)

    # Calculate the number of occupied rooms
    merged_data['OCCUPIED_ROOMS'] = merged_data['RESERVATION_COUNT'] - merged_data['CANCELLATION_COUNT']

    return merged_data

def calculate_occupancy_percentage(hotel_data, target_day, total_rooms,days_limit):

    """Calculate cumulative reserved rooms and occupancy percentage."""
    merged_data = calculate_occupied_rooms(hotel_data,target_day,days_limit)
    merged_data['CUMULATIVE_RESERVED_ROOMS'] = merged_data['OCCUPIED_ROOMS'].cumsum()

    # Calculate occupancy percentage
    occupancy_percentage = (merged_data['CUMULATIVE_RESERVED_ROOMS'] / total_rooms) * 100

    return merged_data.DATE_OF_RESERVATION, occupancy_percentage



def generate_booking_curve(hotel_data, target_day, total_rooms, days_limit):
    """Generate booking curve using the occupancy percentage of target date and one year prior."""
    
    # Calculating one year prior date
    one_year_prior_date = target_day - timedelta(days=365)
    
    # Calculate occupancy for the current date
    date, occupancy_percentage = calculate_occupancy_percentage(hotel_data, target_day, total_rooms,days_limit)
    
    # Calculate occupancy for the previous year
    date_previous_year, occupancy_percentage_previous_year = calculate_occupancy_percentage(hotel_data, one_year_prior_date, total_rooms,days_limit)

    # For visualization of two curves, remove year from dates
    date_no_year = pd.to_datetime(date.dt.strftime('%m-%d'), format='%m-%d')
    date_previous_year_no_year = pd.to_datetime(date_previous_year.dt.strftime('%m-%d'), format='%m-%d')

    # Plotting
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(date_no_year, occupancy_percentage, label=f'Booking Curve - {target_day.date()}', color='blue')
    ax.plot(date_previous_year_no_year, occupancy_percentage_previous_year, label=f'Booking Curve - {one_year_prior_date.date()}', color='orange')

    ax.set_title(f'Booking Curve - {target_day.date()} and {one_year_prior_date.date()}')
    ax.set_xlabel('Date')
    ax.set_ylabel('Occupancy (%)')
    ax.legend()
    ax.grid(True)

    # Use DayLocator to set ticks every 10 days
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=10))
    #
    # Use DateFormatter to format the ticks as '%b %d' (month and day)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
    plt.show()
    fig.savefig("booking_curve.png")
    return fig

def generate_booking_curve_with_datePicker(hotel_data, target_day, total_rooms, days_limit):
    """Generate booking curve using the occupancy percentage of target date and one year prior where date is selected using datepicker"""
    app = dash.Dash(__name__)

    app.layout = html.Div([
        dcc.DatePickerSingle(
            id='date-picker',
            date=target_day.date(),
        ),
        dcc.ConfirmDialog(id='booking-curve',message="Continue?")
  
    ])

    @app.callback(
        Output('booking-curve', 'displayed'),
        [Input('date-picker', 'date')]
    )
    
    def update_booking_curve(selected_date):        
        selected_date = datetime.strptime(selected_date, '%Y-%m-%d')
        generate_booking_curve(hotel_data, selected_date, total_rooms, days_limit)
    
        return False

    #running app
    app.run_server(debug=True)

def generate_booking_curves_for_month_year(target_year,target_month,hotel_data,total_rooms, days_limit):
    """Generate booking curves for given target month and year."""
 
    fig, ax = plt.subplots(figsize=(15, 8))
    number_of_days = days_in_month(target_year, target_month)
    for day in range(1, number_of_days+1):
        target_day = datetime(target_year, target_month, day)
        date_day, occupancy_percentage_day = calculate_occupancy_percentage(hotel_data, target_day,total_rooms, days_limit)
        ax.plot(date_day, occupancy_percentage_day, label=f'Day {day}')

    ax.set_title(f'Booking Curves for '+ month_name_from_number(target_month)+' '+str(target_year) )
    ax.set_xlabel('Date')
    ax.set_ylabel('Occupancy (%)')
    ax.legend()
    ax.grid(True)

    # Use DayLocator to set ticks every 10 days
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=10))

    # Use DateFormatter to format the ticks as '%b %d' (month and day)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
    
    plt.show()

# def generate_booking_heatmap(hotel_data, total_rooms):
#     """Generate a heatmap for booking trends in July."""
#     target_month = datetime(2022, 7, 1)
#     days_in_month = pd.date_range(target_month, target_month + pd.DateOffset(days=30), freq='D')

#     occupancy_matrix = np.zeros((len(days_in_month), total_rooms))

#     for i, target_day in enumerate(days_in_month):
#         _, occupancy_percentage_day = calculate_occupancy_percentage(hotel_data, target_day,total_rooms, 100)
#         occupancy_matrix[i, :len(occupancy_percentage_day)] = occupancy_percentage_day.values

#     fig, ax = plt.subplots(figsize=(15, 8))
#     sns.heatmap(occupancy_matrix, cmap="YlGnBu", ax=ax, cbar_kws={'label': 'Occupancy (%)'})
    
#     ax.set_title('Booking Trend - July 2022')
#     ax.set_xlabel('Room')
#     ax.set_ylabel('Day')
    
#     plt.show()

def main():

    #Reading the hotel data
    file_path = 'reservation_data_sample.csv'
    data = read_data(file_path)

    #define the limit of booking curve x-axis value (number of prior days to the defined target date)
    days_limit = 100

    #Data preprocessing
    hotel_data = preprocessing(data)

    # Calculating total number of unique rooms present at the hotel
    total_rooms = len(hotel_data['ROOM_ID'].unique())

    # Specify the target day
    target_day = datetime(2022, 7, 16)

    # Generate booking curve and calculate cumulative available rooms
    #generate_booking_curve(hotel_data, target_day, total_rooms, days_limit)

    target_year= 2022
    target_month = 7

    
    #generate_booking_heatmap(hotel_data, total_rooms)

    #uncomment following function to see booking curves for all the days of provided target year and month
    # Generate booking curve for provided year and month for all the days
    #generate_booking_curves_for_month_year(target_year,target_month,hotel_data,total_rooms, days_limit)

    #uncomment following function to see run simple app which allows you to select datepicker that aids in generating booking curve for selected date
    # Generate booking curve for selected date using data picker
    generate_booking_curve_with_datePicker(hotel_data, target_day, total_rooms, days_limit)

    
if __name__ == "__main__":
    main()
