#!/usr/bin/env python
# coding: utf-8

import pandas as pd
import numpy as np
import geopandas as gpd
import datetime as dt
import json
import math
from bokeh.io import output_notebook, show, output_file
from bokeh.plotting import figure
from bokeh.models import GeoJSONDataSource, LinearColorMapper, ColorBar, NumeralTickFormatter
from bokeh.palettes import brewer
from bokeh.io.doc import curdoc
from bokeh.models import Slider, HoverTool, Select
from bokeh.layouts import widgetbox, row, column

pd.set_option('max_columns', 180)
pd.set_option('max_rows', 200000)
pd.set_option('max_colwidth', 5000)

# ## Geopandas
shapefile = 'ga_data/county_shp/Counties_Georgia.shp'

#Read shapefile using Geopandas
gdf = gpd.read_file(shapefile)[['GEOID10', 'NAME10', 'geometry']]
gdf.iloc[0]

#Rename columns.
gdf.columns = ['fips', 'county_code', 'geometry']
gdf['fips'] = gdf['fips'].astype(int)

# ## Import Dataframes
# summary = pd.read_csv('https://raw.githubusercontent.com/briannaleilani/ga_covid_dash/master/georgia.csv')
counties = pd.read_csv('ga_90days_map.csv')

# Get the most recent day
date_day = pd.read_csv('/Users/brileilani/Desktop/Coronavirus/date_dict.csv')
date = pd.to_datetime(date_day["Date"], dayfirst=True)
date_s = date.dt.strftime('%m/%d/%Y').tolist()
day_dict = dict(zip(date_s, range(1,len(date_s)+1))) # DATES AS KEYS

today = pd.Timestamp.today().strftime("%m/%d/%Y")
most_recent = day_dict[today] 

# ## Create a Formatting DataFrame
# This dictionary contains the formatting for the data in the plots
format_data = [('TotalCases', 1, 100,'0,0', 'Number of Confirmed Coronavirus Cases'),
               ('TotalDeaths', 1, 10,'0,0', 'Number of Confirmed Coronavirus Deaths'),
               ('nConfirmed_Change', 1, 100, '0,0', 'Daily Increase in Cases'),
               ('nDeaths_Change', 1, 15,'0,0', 'Daily Increase in Deaths')
              ]
 
# Create a DataFrame object from the dictionary 
format_df = pd.DataFrame(format_data, columns = ['field' , 'min_range', 'max_range' , 'format', 'verbage'])


# Define function that returns json_data for the day since the coronavirus outbreak started in Georgia, defined by user
def json_data(selected_day):
    day = selected_day
    
    # Pull selected day from `counties` data
    df_day = counties[counties['Day'] == day] 
    
    # Merge GeoDataframe object (gdf) with `counties` data
    merged = gdf.merge(df_day, on='fips') 
    
    # Fill the null values
    values = {'Date': 0, 'Day': day, 'Population': 0, 'TotalCases': 0, 'TotalDeaths': 0, 'PctPopInfected': 0, 
              'Infection_per_100k': 0, 'Deaths_per_100k': 0, 'Deaths_per_100_Infections': 0, 
              'nConfirmed_Change': 0, 'nDeaths_Change': 0, 'pConfirmed_Change': 0, 'pDeaths_Change': 0, 'Fatality_Rate': 0}
    merged = merged.fillna(value=values)
    
    # Convert to json
    json_data = merged.to_json()
    return json_data

# # Interactive Map
def update_plot(attr, old, new):
    # The input `day` is the day selected from the slider
    day = slider.value
    new_data = json_data(day)
    
    # The input cr is the criteria selected from the select box
    cr = select.value
    input_field = format_df.loc[format_df['verbage'] == cr, 'field'].iloc[0]
    
    # Update the plot based on the changed inputs
    p = make_plot(input_field)
    
    # Update the layout, clear the old document and display the new document
    layout = column(p, widgetbox(select), widgetbox(slider))
    curdoc().clear()
    curdoc().add_root(layout)
    
    # Update the data
    geosource.geojson = new_data


# ## Define the plotting function: make_plot
def make_plot(field_name):
    # Set the format of the colorbar
    min_range = format_df.loc[format_df['field'] == field_name, 'min_range'].iloc[0]
    max_range = format_df.loc[format_df['field'] == field_name, 'max_range'].iloc[0]
    field_format = format_df.loc[format_df['field'] == field_name, 'format'].iloc[0]
    
    #Instantiate LinearColorMapper that linearly maps numbers in a range, into a sequence of colors. Input nan_color.
    color_mapper = LinearColorMapper(palette = palette, low = min_range, high = max_range, low_color = '#F7F6F6')
    
    # Create color bar
    format_tick = NumeralTickFormatter(format=field_format)
    color_bar = ColorBar(color_mapper=color_mapper, label_standoff=18, formatter=format_tick, border_line_color=None, location = (0, 0))
    
    # Create figure object
    verbage = format_df.loc[format_df['field'] == field_name, 'verbage'].iloc[0]
    p = figure(title = 'Daily Spread of the Coronavirus Outbreak throughout Georgia', 
               plot_height = 900, plot_width = 750, toolbar_location = None)
    p.xgrid.grid_line_color = None
    p.ygrid.grid_line_color = None
    p.axis.visible = False
    
    # Add patch renderer to figure. 
    p.patches('xs','ys', source = geosource,fill_color = {'field' : field_name, 'transform' : color_mapper},
              line_color = 'black', line_width = 0.25, fill_alpha = 1)
    
    # Specify color bar layout
    p.add_layout(color_bar, 'right')
    
    # Add the hover tool to the graph
    p.add_tools(hover)
    
    return p


# ## Main Code for Interactive Map
# Input GeoJSON source that contains features for plotting for: current day and initial criteria for `Confirmed`
geosource = GeoJSONDataSource(geojson = json_data(most_recent))
input_field = 'TotalCases'

# Define a sequential multi-hue color palette
palette = brewer['YlGnBu'][8]

# Reverse color order so that dark blue represents the highest figures
palette = palette[::-1]

# Add hover tool
hover = HoverTool(tooltips = [ ('County','@County'),
                               ('# Cases', '@TotalCases'),
                               ('# Deaths', '@TotalDeaths'),     
                               ('# Daily Case Increase', '@nConfirmed_Change'),     
                               ('# Daily Daily Increase', '@nConfirmed_Change'),     
                            ])

# Call the plotting function
p = make_plot(input_field)

# Make a slider object: slider 
slider = Slider(title='Day', start=1, end=most_recent, step=1, value=most_recent)
slider.on_change('value', update_plot)

# Make a selection object: select
select = Select(title='Select Criteria:', value='Number of Confirmed Coronavirus Cases', options=['Number of Confirmed Coronavirus Cases', 'Number of Confirmed Coronavirus Deaths',
                                                                               'Daily Increase in Cases', 'Daily Increase in Deaths'])
select.on_change('value', update_plot)
 
# Make a column layout of widgetbox(slider) and plot, and add it to the current document
layout = column(p, widgetbox(select), widgetbox(slider))

# Display the current document
curdoc().add_root(layout)

# # Use the following code to test in a notebook, comment out for transfer to live site as interactive features will not show in notebook
# output_notebook()
# show(p)

# # Static Map
# ## Static Chloropleth Map for Today
# Filter out the most recent values:
# counties = counties[counties["Day"] == most_recent]

# # merge geopandas dataframe with counties data
# merged = gdf.merge(counties, on="fips")

# merged['Date'] = str(merged['Date'])
# json_data = merged.to_json()

# #Input GeoJSON source that contains features for plotting.
# geosource = GeoJSONDataSource(geojson = json_data)
# #Define a sequential multi-hue color palette.
# palette = brewer['YlGnBu'][8]
# #Reverse color order so that dark blue is highest obesity.
# palette = palette[::-1]
# #Instantiate LinearColorMapper that linearly maps numbers in a range, into a sequence of colors.
# color_mapper = LinearColorMapper(palette = palette, low = 1, high = 100, low_color = '#F7F6F6')
# #Create color bar. 
# color_bar = ColorBar(color_mapper=color_mapper, label_standoff=8,width = 650, height = 20,
# border_line_color=None,location = (0,0), orientation = 'horizontal')
# # , major_label_overrides = steps
# #Create figure object.
# p = figure(title = 'Number of Confirmed Coronavirus Cases in Georgia', plot_height = 900 , plot_width = 650, toolbar_location = None)
# p.xgrid.grid_line_color = None
# p.ygrid.grid_line_color = None
# #Add patch renderer to figure. 
# p.patches('xs','ys', source = geosource,fill_color = {'field' :'TotalCases', 'transform' : color_mapper},
#           line_color = 'black', line_width = 0.25, fill_alpha = 1)
# #Specify figure layout.
# p.add_layout(color_bar, 'below')
# #Display figure inline in Jupyter Notebook.
# output_notebook()
# #Display figure.
# show(p)