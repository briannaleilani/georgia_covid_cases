#!/usr/bin/env python
# coding: utf-8

# # Import Modules and Data

# In[3]:


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


shapefile = 'ga_data/county_shp/Counties_Georgia.shp'

#Read shapefile using Geopandas
gdf = gpd.read_file(shapefile)[['GEOID10', 'NAME10', 'geometry']]
gdf.iloc[0]

#Rename columns.
gdf.columns = ['fips', 'county_code', 'geometry']
gdf['fips'] = gdf['fips'].astype(int)
gdf.head(1)


# ## Import Dataframes
# add day count starting from 19 on 22nd
summary = pd.read_csv('ga_data/output/ga_cases_summary.csv')
counties = pd.read_csv('ga_data/output/ga_county_cases.csv')

# clean data for visualization
counties.fillna(0, inplace=True)
most_recent = counties["Day"].max()


# ## Create a Formatting DataFrame
# This will be used to adjust the ColorBar values. Each criteria has it’s own unique minimum and maximum range, format for displaying and verbage. 

# This dictionary contains the formatting for the data in the plots
format_data = [('Confirmed', 1, 100,'0,0', 'Number of Confirmed Coronavirus Cases'),
               ('Deaths', 1, 10,'0,0', 'Number of Confirmed Coronavirus Deaths'),
               ('Fatality_Rate', 0.01, 100, '0.00', 'Coronavirus Fatality Rate (Deaths/Confirmed)'),
               ('pConfirmed_Change', 0.01, 100,'0.00', 'Percent Daily Change in Coronavirus Cases')
              ]
 
# Create a DataFrame object from the dictionary 
format_df = pd.DataFrame(format_data, columns = ['field' , 'min_range', 'max_range' , 'format', 'verbage'])

# ## Create the JSON Data for the GeoJSONDataSource
# Define function that returns json_data for the day since the coronavirus outbreak started in Georgia, defined by user
def json_data(selected_day):
    day = selected_day
    
    # Pull selected day from `counties` data
    df_day = counties[counties['Day'] == day] 
    
    # Merge GeoDataframe object (gdf) with `counties` data
    merged = gdf.merge(df_day, on='fips') 
    
    # Fill the null values
    values = {'Day': day, 'Confirmed': 0, 'Deaths': 0, 'Recovered': 0, 'Active': 0, 'Fatality_Rate': 0, 
              'nConfirmed_Change': 0, 'nDeaths_Change': 0, 'nRecovered_Change': 0, 
              'pConfirmed_Change': 0, 'pDeaths_Change': 0, 'pRecovered_Change': 0}
    merged = merged.fillna(value=values)
    
    # Convert datetime object to string as json object doesn't except datetime values
    merged['Date'] = str(merged['Date'])
    
    # Convert to json
    json_data = merged.to_json()
    return json_data

# # Interactive Map
# ## Define the callback function: update_plot
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
input_field = 'Confirmed'

# Define a sequential multi-hue color palette
palette = brewer['YlGnBu'][8]

# Reverse color order so that dark blue represents the highest figures
palette = palette[::-1]

# Add hover tool
hover = HoverTool(tooltips = [ ('County','@County'),
                               ('# Cases', '@Confirmed'),
                               ('# Deaths', '@Deaths'),     
                               ('% Fatality', '@Fatality_Rate'),     
                               ('% Daily Change', '@pConfirmed_Change'),     
                            ])

# Call the plotting function
p = make_plot(input_field)

# Make a slider object: slider 
slider = Slider(title='Day', start=19, end=most_recent, step=1, value=most_recent)
slider.on_change('value', update_plot)

# Make a selection object: select
select = Select(title='Select Criteria:', value='Number of Confirmed Cases', options=['Number of Confirmed Coronavirus Cases', 'Number of Confirmed Coronavirus Deaths',
                                                                               'Coronavirus Fatality Rate (Deaths/Confirmed)', 'Percent Daily Change in Coronavirus Cases'])
select.on_change('value', update_plot)
 
# Make a column layout of widgetbox(slider) and plot, and add it to the current document
layout = column(p, widgetbox(select), widgetbox(slider))

# Display the current document
curdoc().add_root(layout)

# Use the following code to test in a notebook, comment out for transfer to live site as interactive features will not show in notebook
# output_notebook()
# show(p)