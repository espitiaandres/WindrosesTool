import pandas as pd
from matplotlib import pyplot as plt
from windrose import WindroseAxes
import numpy as np
import os, sys, getopt, time

# Initialize subplot titles for different different data sampling intervals
months_titles = ["January", "February", "March", "April", "May", "June", 
                  "July", "August", "September", "October", "November", "December"]
seasons_titles = ["Winter: Jan-Mar", "Spring: Apr-Jun", "Summer: Jul-Sep", "Autumn: Oct-Dec"]
unsectioned_title = ["Data"]
plot_variables = []
data_sampling_intervals = ['months', 'seasons', 'unsectioned']
data_sampling_interval, radial_var, direction_var, date_time_var = None, '', '', ''
script_options_info = ("""
************************
WindrosesPython.py required arguments
   
-f <raw_file_name>            -> string   ex: "alert_winds.txt"
-y <time_range>               -> string   ex: "2000-2019"
-p <plot_suptitle>            -> string   ex: "Monthly Windroses Plots from Alert, NU"
-r <radial_var>               -> string   ex: "speed_knots" (column name in raw data file that contains radial variable data)
-d <direction_var>            -> string   ex: "direction" (column name in raw data file that contains direction variable data)
-t <date_time_var>            -> string   ex: "date_time" (column name in raw data file that contains date time variable data)
-l <legend_title>             -> string   ex: "Wind Speed in knots"
-b <bin_number>               -> integer  ex: 24 (must be positive and nonzero integer)
-i <legend_intervals>         -> integer  ex: 6 (must be positive and nonzero integer)
-s <data_sampling_interval>   -> string   ex: months, seasons, unsectioned. Seasons are divided
                                              into 3 months, such as January - March is Winter, 
                                              April - June is Spring, and so on.

Example: if your data looks like this,
station| date_time       | direction| speed_knots
-------|-----------------|----------|------------
CYLT   | 2000-01-04 12:00| 200      | 2
CYLT   | 2000-01-04 13:00| 150      | 4
CYLT   | 2000-01-04 14:00| 190      | 3

-r would be "speed_knots"
-d would be "direction"
-t would be "date_time"
************************""")



# Validates date time variable when doing multiple subplots
def validate_date_time_var(date_time_var, data_sampling_interval, file_column_headers):
    validated = False
    if date_time_var == '':
        print("Provide a date time variable. To do this, enter the name of the variable"
              + " from the raw data column name that contains the time stamp of the data collected. \n")
    elif date_time_var not in file_column_headers:
        print("Provide the date time variable column name found in the raw data file \n")
    else:
        validated = True
    validation_failure(validated, file_column_headers)
    return


# Validates radial and direction variables entered
def validate_plot_variables(radial_var, direction_var, file_column_headers):
    validated = False
    if radial_var not in file_column_headers and direction_var not in file_column_headers:
        print("Invalid radial and direction variable inputs. Please choose the correct headers from the file corresponding to each radial variable:\n")
    elif radial_var not in file_column_headers:
        print("Invalid radial variable input. Please choose the header from the file corresponding to the radial variable:\n")
    elif direction_var not in file_column_headers:
        print("Invalid directional variable input. Please choose the header from the file corresponding to the radial variable:\n")
    else:
        validated= True
    validation_failure(validated, file_column_headers)
    return


# Displays the headers of the file to the user. Exits program if user input validation fails
def validation_failure(validated, file_column_headers):
    if not validated:
        print(file_column_headers)
        sys.exit()
    return


# Parses data on a monthly basis
def monthly_data_parsing(df, date_time_var):
    data_arrays = section_arrays(months_titles)
    for i in range(len(data_arrays.wd_array)):
        data_arrays.df_array[i] = df[pd.to_datetime(df[date_time_var]).dt.month == i+1]
    return data_arrays


# Parses data on a seasonal basis, where each seasons is grouped into 3 months (Winter = January - March, etc.)
def seasonal_data_parsing(df, date_time_var):
    data_arrays = section_arrays(seasons_titles)
    for i in range(len(data_arrays.wd_array)):    
        data_arrays.df_array[i] = (df[pd.to_datetime(df[date_time_var]).dt.month == 3*i+1]
                       .append(df[pd.to_datetime(df[date_time_var]).dt.month == 3*i+2])
                       .append(df[pd.to_datetime(df[date_time_var]).dt.month == 3*i+3]))
    return data_arrays


# Parses all collected data in 1 dataframe
def unsectioned_data_parsing(df):
    data_arrays = section_arrays(unsectioned_title)
    data_arrays.df_array[0] = df
    return data_arrays


# Filters data to be plotted
def filtered_plot_data(data_arrays, intervals_titles):
    max_wind_radius_unit_legend = value_filtering(data_arrays, intervals_titles)
    plot_data = PlotData(data_arrays.wd_array, data_arrays.wr_array, max_wind_radius_unit_legend)
    return plot_data


# Creates however many wr and wd arrays needed for each time interval: months, seasons, unsectioned, etc.
def section_arrays(intervals_titles):
    wr_array, wd_array, df_array = [], [], []
    for i in range(len(intervals_titles)):
        wr_array.append([])
        wd_array.append([])
        df_array.append([])
    data_arrays = RawDataArrays(df_array, wd_array, wr_array)
    return data_arrays


# Filtering through NaN values, also filtering through each dataframe based on a 0 wind speed
def value_filtering(data_arrays, intervals_titles):
    df_array, wd_array, wr_array = data_arrays.df_array, data_arrays.wd_array, data_arrays.wr_array
    interval_max_wind_radius_unit = []
    for i in range(len(wd_array)):
        radial_and_direction_values = [df_array[i][plot_variables[0]].values, df_array[i][plot_variables[1]].values, wr_array[i], wd_array[i]]
        intervals_data = [i, intervals_titles]
        convert_string_values_to_float(radial_and_direction_values, intervals_data)
        df_array[i] = df_array[i][df_array[i][plot_variables[0]] != "0.00"]
        
        # If radial variable (example: wind speed) is 0, make wind direction 0 as well so that this value is not plotted
        for j in range(len(wr_array[i])):
            if wr_array[i][j] == 0.0:
                wd_array[i][j] = 0.0
        if not wr_array[i]:
            print("Cannot do multiplot as some plots would be empty. If you do not have data " 
                  + " for all months/seasons, please enter \"unsectioned\" for the -s argument.\n")
            sys.exit()
        interval_max_wind_radius_unit.append(max(wr_array[i]))
        
        
    # round up to the nearest multiple of 5
    max_wind_radius_unit_legend = max(interval_max_wind_radius_unit)
    return max_wind_radius_unit_legend


# Set up pyplot parameters such as height, width, font size, etc. to plot windroses for each month
def pyplot_figure_settings(plot_suptitle, title_x_value):
    fig = plt.figure()
    fig.set_size_inches(16.5, 10.5, forward=True)
    fig.suptitle(plot_suptitle, fontsize=24, y=1, x=title_x_value)
    plt.subplots_adjust(left=0, right=1.1, wspace=-0.7, hspace=0.4, top=0.91)
    return fig


# Converts string values read from the raw data file to float values.
def convert_string_values_to_float(radial_and_direction_values, intervals_data):
    wr_string, wd_string = radial_and_direction_values[0], radial_and_direction_values[1]
    wr, wd = radial_and_direction_values[2], radial_and_direction_values[3]
    interval_number, intervals_titles = intervals_data[0], intervals_data[1]
    for i in range(len(wr_string)):
        try:
            float(wr_string[i])
            float(wd_string[i])
        except:
            print(('At line '+ str(i) + ' in ' + str(intervals_titles[interval_number]) + 
                   ', there are possible non number values: speed_knots = ' + str(wr_string[i]) + 
                   ' and direction = ' + str(wd_string[i]) + '\n'))
            wr_string[i], wd_string[i] = '0', '0'
        finally:
            wr.append(float(wr_string[i]))
            wd.append(float(wd_string[i]))
    return


""" CONTROLLERS """
# Controller responsible for setting up filtered data and data plotting
class PlotData:
    def __init__(self, wd_array, wr_array, max_wind_radius_unit_legend):
        self.wd_array = wd_array
        self.wr_array = wr_array
        self.max_wind_radius_unit_legend = max_wind_radius_unit_legend
        
    #Plot windroses, output to png file
    def windrose_plotting(self, plot_parameters, titles):
        fig = pyplot_figure_settings(titles.plot_suptitle, titles.title_x_value)
        output_file_name = (os.path.splitext(plot_parameters.raw_file_name)[0] + "_" 
                            + plot_parameters.data_sampling_interval + "_windrose_plot.png")
        ax, legend_location = None, "right"
        plt.rc('xtick', labelsize=titles.x_tick_labelsize)
        plt.rc('ytick', labelsize=titles.y_tick_labelsize)
        
        # Define subplots size based on monthly, seasonal intervals
        if plot_parameters.data_sampling_interval == data_sampling_intervals[0]:
            rows, cols, legend_x_pos, legend_y_pos, legend_font, legend_title_font = 3, 4, 1.5, 1.2, 10, "11"
            time_interval = months_titles
        elif plot_parameters.data_sampling_interval == data_sampling_intervals[1]:
            rows, cols, legend_x_pos, legend_y_pos, legend_font, legend_title_font = 2, 2, 0.98, 0.46, 10, "11"
            time_interval = seasons_titles
        elif plot_parameters.data_sampling_interval == data_sampling_intervals[-1]:
            rows, cols, legend_x_pos, legend_y_pos, legend_font, legend_title_font = 1, 1, 0.83, -0.25, 14, "14"
            time_interval = unsectioned_title  
        
        # Loop through the data sampling intervals (monthls, seasonal) to create corresponding subplots
        for time_period in range(len(self.wd_array)):
            ax = fig.add_subplot(rows, cols, time_period+1, projection='windrose')
            ax.set_title(time_interval[time_period] + " " + plot_parameters.time_range, 
                         fontsize=14, y=titles.subtitle_y_value, x=titles.subtitle_x_value)
            ax.bar(self.wd_array[time_period], self.wr_array[time_period], 
                   bins=np.arange(1, self.max_wind_radius_unit_legend, 
                   (self.max_wind_radius_unit_legend-1)/plot_parameters.legend_intervals), 
                   normed=True, opening=0.8, nsector=plot_parameters.bin_number, 
                   edgecolor='white', label=time_interval[time_period])
        ax.legend(loc=legend_location, bbox_to_anchor=(legend_x_pos, legend_y_pos, 0.5, 1.5), 
                  fontsize=legend_font, title=plot_parameters.legend_title, title_fontsize=legend_title_font)
        fig.savefig(output_file_name, dpi=100, bbox_inches="tight")
        return
    
    
""" MODELS """
# Stores plot data values
class RawDataArrays():
    def __init__(self, df_array, wd_array, wr_array):
        self.df_array = df_array
        self.wd_array = wd_array
        self.wr_array = wr_array
      
# Stores title labels, location values, and label font sizes
class Titles():
    def __init__(self, subtitle_y_value, subtitle_x_value, title_x_value, plot_suptitle, x_tick_labelsize, y_tick_labelsize):
        self.subtitle_y_value = subtitle_y_value
        self.subtitle_x_value = subtitle_x_value
        self.title_x_value = title_x_value
        self.plot_suptitle = plot_suptitle
        self.x_tick_labelsize = x_tick_labelsize
        self.y_tick_labelsize = y_tick_labelsize
        
# Stores plot parameters, legend configuration, and type of plot/output.
class PlotParameters():
    def __init__(self, legend_intervals, bin_number, legend_title, raw_file_name, time_range, data_sampling_interval):
        self.legend_intervals = legend_intervals
        self.bin_number = bin_number
        self.legend_title = legend_title
        self.raw_file_name = raw_file_name
        self.time_range = time_range
        self.data_sampling_interval = data_sampling_interval
        

# Main function that uses pandas to read the data, and pyplot to plot the windroses        
def main(argv):
    t = time.time()
    df = None
    
    # Parses through arguments passed in to getopt, troubleshoots getoptError and generic errors in catch statements
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'f:y:p:r:d:t:l:b:i:s:h', [""])
    except getopt.GetoptError as err:
        print(err)
        print(script_options_info)
        sys.exit(2)
    except Exception as e:
        print(e)
        sys.exit(2)
    for opt, arg in opts:
        if opt=='-h':
            print(script_options_info)
            sys.exit()
        elif opt in ('-f'):
            raw_file_name = arg
        elif opt in ('-y'):
            time_range = arg
        elif opt in ('-p'):
            plot_suptitle = arg
        elif opt in ('-r'):
            radial_var = arg
        elif opt in ('-d'):
            direction_var = arg
        elif opt in ('-t'):
            date_time_var = arg
        elif opt in ('-l'):
            legend_title = arg
        elif opt in ('-b'):
            try:
                bin_number = int(arg)
            except:
                bin_number = 24
        elif opt in ('-i'):
            try:
                legend_intervals = int(arg)
            except:
                legend_intervals = 6
        elif opt in ('-s'):
            data_sampling_interval = arg.lower()
        
    # Stop the program if invalid sampling interval entered
    if data_sampling_interval not in data_sampling_intervals:
        print('Invalid sampling interval (-s argument). Try something like months, seasons, or unsectioned instead')
        sys.exit()   
        
    # Stop the program if radial and/or direction variables are not entered.
    elif not radial_var or not direction_var:
        print(('Provide both a radial and a directional variable to plot. ' 
               + 'To do this, enter the names of those variables from the raw data file column names.'))
        sys.exit()
    
    # Read csv file using pandas, throws an error if the file does not exist
    try:
        df = pd.read_csv(raw_file_name, delimiter=",")
        file_column_headers = list(df.columns.values)
    except:
        print("Error in trying to read the file: ", sys.exc_info()[1])
        sys.exit()   

    #Validating user inputs for the radial, direction, and date time variables.
    validate_plot_variables(radial_var, direction_var, file_column_headers)
    if data_sampling_interval != data_sampling_intervals[-1]:
        validate_date_time_var(date_time_var, data_sampling_interval, file_column_headers)
    plot_suptitle += " " + time_range 
    plot_variables.extend((radial_var, direction_var))
    
    # Setting up different parsing functions for each data interval, and subplot formatting
    if data_sampling_interval == data_sampling_intervals[0]:
        titles = Titles(1.12, 0.5, 0.60, plot_suptitle, 12, 12)
        monthly_data_arrays = monthly_data_parsing(df, date_time_var)
        plot_values = filtered_plot_data(monthly_data_arrays, months_titles)
    elif data_sampling_interval == data_sampling_intervals[1]:
        titles = Titles(1.1, 0.5, 0.59, plot_suptitle, 14, 14)
        seasonal_data_arrays = seasonal_data_parsing(df, date_time_var)
        plot_values = filtered_plot_data(seasonal_data_arrays, seasons_titles)
    elif data_sampling_interval == data_sampling_intervals[-1]:
        titles = Titles(1, 0.6, 0.61, plot_suptitle, 16, 16)
        unsectioned_data_arrays = unsectioned_data_parsing(df)
        plot_values = filtered_plot_data(unsectioned_data_arrays, unsectioned_title)
    
    # Creates plot_parameters object to begin plotting Windroses. elapsed variable displays user how long the entire process took.
    plot_parameters = PlotParameters(legend_intervals, bin_number, legend_title, raw_file_name, time_range, data_sampling_interval)
    plot_values.windrose_plotting(plot_parameters, titles)
    print('Plotted! Check the raw file folder.\n')
    elapsed = time.time() - t
    print("Time taken: " + str(elapsed) + " seconds.")
    return


# Program entry point
if __name__ == "__main__":
    main(sys.argv[1:])
    
