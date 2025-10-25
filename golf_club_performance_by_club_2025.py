# %%
import pandas as pd
import numpy as np
import glob
import os
import warnings
warnings.filterwarnings('ignore')


# %%
folder_path = "/folder/path.data_type" #insert the correct directory path between the brackets e.g., {{"file_path"}}
csv_files = glob.glob(os.path.join(folder_path, '{data_used}*.csv')) #glob joins all the files from the folder_path location. add the naming convention of your file path e.g., {{'naming_convetion*.file_type}}
merged_ydg = pd.concat((pd.read_csv(f) for f in  csv_files), ignore_index=True) #concatenate the csv files into a merged df

print(f"Merged {len(csv_files)} files into one dataframe with {len(merged_ydg)} rows.")

# %%
merged_ydg.head()

# %% [markdown]
# ### *Notes*:
# 
# #### In the code above, you can see that there are two columns ostensibly presenting the same data 'Club Name' and 'Club Type'. 'Club Name' has missing values whereas 'Club Type' has usable data. There is also a row at loc[0] which conists of no values with some enumeration (e.g., [mph], [deg]). There are also columns such as 'Note' and 'Tag'; however, these columns has missing values and can be dropped as part of additional ETL.

# %%
"""
Cell Note:

This cell drops columns that aren't need, lack data, or simply aren't required for whatever type of analysis being conducted. 
For my sake, I've dropped Club Name, Note, Tag, and Relative Humidity.
"""
merged_ydg.drop(columns=['Club Name', 'Note', 'Tag', 'Relative Humidity'], inplace=True)

# %%
# This cell is dropping 'na' value from rows which have no data
merged_ydg.dropna()

# %% [markdown]
# ### In the code and results above, now at loc[1], the usable data for analysis beings. However, further ETL needs to be conducted to make this data usable. You will need to convert columns to a desired data type (see the cell below).

# %%
# Columns to convert
cols_to_convert = ['Club Speed', 'Attack Angle', 'Club Path', 'Club Face', 'Face to Path',	'Ball Speed', 'Launch Angle', 'Launch Direction', 'Backspin', 'Sidespin', 'Spin Rate', 'Spin Rate Type', 'Spin Axis', 'Apex Height', 'Carry Distance', 'Carry Deviation Angle', 'Carry Deviation Distance', 'Total Distance', 'Total Deviation Angle', 'Total Deviation Distance', 'Air Density', 'Temperature', 'Air Pressure']

# Convert selected columns to numeric, coercing errors to NaN
merged_ydg[cols_to_convert] = merged_ydg[cols_to_convert].apply(pd.to_numeric, errors='coerce')

# If specific integer type is needed (e.g., int32, int64), use astype after to_numeric
merged_ydg[cols_to_convert] = merged_ydg[cols_to_convert].fillna(0).astype(int)

# %% [markdown]
# ### In the cell below we will inspect the data using 'info' to see how many records there 'Non-Null Count' and what type of data is in each columns 'Dtype'.

# %%
merged_ydg.info()

# %%
merged_ydg = merged_ydg.round(2) #rounds each columns with a numerica data type to two decimals
merged_ydg = merged_ydg.dropna()
merged_ydg.to_csv('/folder/path.data_type')

# %% [markdown]
# ### Analysis
# 
# In the cell below the calculation for average carry yds by club type is executed.

# %%
avg_carry_yds = merged_ydg.groupby('Club Type')['Carry Distance'].mean()
avg_carry_yds = avg_carry_yds.round(2)
avg_carry_yds

# %% [markdown]
# One can also analyse the average ball speed, spin rate, apex height, and club speed for additional performance analytics. This type of additional analysis can be conducted against any usable data in your data frame to answer the performance related questions you're looking for.

# %%
avg_ballspeed = merged_ydg.groupby('Club Type')['Ball Speed'].mean()
avg_spinrate = merged_ydg.groupby('Club Type')['Spin Rate'].mean()
avg_apex = merged_ydg.groupby('Club Type')['Apex Height'].mean()
avg_clubspeed = merged_ydg.groupby('Club Type')['Club Speed'].mean()

# %% [markdown]
# In the cell below, I am calculating each clubs average yardage and grouping by the specific columns.

# %%
club_avgs = merged_ydg.groupby('Club Type')[['Carry Distance', 'Ball Speed', 'Spin Rate', 'Apex Height', 'Club Speed']].mean()
club_avgs

# %% [markdown]
# ### The following analysis is looking specifically to answer club gapping questions related to performance.
# 
# **Questions** 
# 
# 1. Where is the biggest gap in my bag?
# 
# 2. Do I have a 10-20yd gap between clubs?
# 
# How do you figure out the ideal yardage gaps for an entire iron set when most fitters are using a 7-iron to determine the setup? During a recent chat on Ping’s Proving Grounds podcast, Marty Jertson, the equipment manufacturer’s VP of fitting and performance, offered up a simple way to determine the best gaps for your iron set.
# 
# “In our data analysis that we’ve done, there’s a good way to figure out your optimal gapping,” Jertson said. “If you go on a launch monitor for a fitting — and we and a lot of our competitors fit with a 7-iron — you take whatever your ball speed is in miles per hour [with a 7-iron] and divide that by 10. That’s a good spacing for your irons.”
# 
# source: https://x.com/PingTour/status/1677044998192128001, https://golf.com/gear/irons/iron-yardage-gaps-ping-jertson/

# %%
"""
This cell sets variables to each club type which makes doing club specific or groups or club analysis easier.
"""

driver = merged_ydg[merged_ydg['Club Type'] == 'Driver']
three_wood = merged_ydg[merged_ydg['Club Type'] == '3 Wood']
three_hi = merged_ydg[merged_ydg['Club Type'] == '3 Hybrid']
three_iron = merged_ydg[merged_ydg['Club Type'] == '3 Iron']
four_iron = merged_ydg[merged_ydg['Club Type'] == '4 Iron']
five_iron = merged_ydg[merged_ydg['Club Type'] == '5 Iron']
six_iron = merged_ydg[merged_ydg['Club Type'] == '6 Iron']
seven_iron = merged_ydg[merged_ydg['Club Type'] == '7 Iron']
eight_iron = merged_ydg[merged_ydg['Club Type'] == '8 Iron']
nine_iron = merged_ydg[merged_ydg['Club Type'] == '9 Iron']
pw = merged_ydg[merged_ydg['Club Type'] == 'Pitching Wedge']
gw = merged_ydg[merged_ydg['Club Type'] == 'Gap Wedge']
sw = merged_ydg[merged_ydg['Club Type'] == 'Sand Wedge']
lw = merged_ydg[merged_ydg['Club Type'] == 'Lob Wedge']

# %% [markdown]
# ### Ideal yardage mapping formula
# 
# **In the cell below I'm going to use Ping's formula to find out my ideal yardage gap for irons.**
# 
# Based on quantitative analysis of my club speed divided by 10, my ideal gap for my irons is 9 yards.
# I have heard that a good gapping to have is 10-20 yards to allow for varied shot types (e.g., 1/2 swing, full swing, laid-off, etc).

# %%
ideal_ydg_gap = seven_iron['Club Speed']/10
float(ideal_ydg_gap.mean().round(2))

# %% [markdown]
# ### In the cells below the gapping from club to club is calculated using the mean calculation. This doesn't take into account the 9yd formula above, this is simply the current average natural gap between clubs based on launch monitor data.

# %%
lw_to_sw = sw['Carry Distance'].mean()-lw['Carry Distance'].mean()
sw_to_gw = gw['Carry Distance'].mean()-sw['Carry Distance'].mean()
gw_to_pw = pw['Carry Distance'].mean()-gw['Carry Distance'].mean()
pw_to_nineiron = nine_iron['Carry Distance'].mean()-pw['Carry Distance'].mean()
nineiron_to_eightiron = eight_iron['Carry Distance'].mean()-nine_iron['Carry Distance'].mean()
eightiron_to_seveniron = seven_iron['Carry Distance'].mean()-eight_iron['Carry Distance'].mean()
seveniron_to_sixiron = six_iron['Carry Distance'].mean()-seven_iron['Carry Distance'].mean()
sixiron_to_fiveiron = five_iron['Carry Distance'].mean()-six_iron['Carry Distance'].mean()
fiveiton_to_fouriron = four_iron['Carry Distance'].mean()-five_iron['Carry Distance'].mean()
fouriron_to_threeiron = three_iron['Carry Distance'].mean()-four_iron['Carry Distance'].mean()
fouriron_to_threehybrid = three_hi['Carry Distance'].mean()-four_iron['Carry Distance'].mean()
threeiron_to_threewood = three_wood['Carry Distance'].mean()-three_iron['Carry Distance'].mean()
threehybrid_to_threewood = three_wood['Carry Distance'].mean()-three_hi['Carry Distance'].mean()
threewood_to_driver = driver['Carry Distance'].mean()-three_wood['Carry Distance'].mean()

# %%
yardage_gaps = {
    "lw_to_sw": lw_to_sw,
    "sw_to_gw": sw_to_gw,
    "gw_to_pw": gw_to_pw,
    "pw_to_nineiron": pw_to_nineiron,
    "nineiron_to_eightiron": nineiron_to_eightiron,
    "eightiron_to_seveniron": eightiron_to_seveniron,
    "seveniron_to_sixiron": seveniron_to_sixiron,
    "sixiron_to_fiveiron": sixiron_to_fiveiron,
    "fiveiron_to_fouriron": fiveiton_to_fouriron,
    "fouriron_to_threeiron": fouriron_to_threeiron,
    "fouriron_to_threehybrid": fouriron_to_threehybrid,
    "threehybrid_to_threewood": threehybrid_to_threewood,
    "threeiron_to_threewood": threeiron_to_threewood,
    "threewood_to_driver": threewood_to_driver
}

print("Current yardage gap by club:")
for label, value in yardage_gaps.items():
    print(f"{label.replace('_', ' ')}: {float(value.round())}")

# %% [markdown]
# ## Wind calculations: Hitting into the wind
# 
# The general rule is to add .01% for every 1mph of headwind. So the following distances would change like this:
# 
# - 100-yard shot into a 5mph wind = 105 yards
# - 200-yard shot into a 5mph wind = 210 yards
# - 100-yard shot into a 10mph wind = 110 yards
# - 200-yard shot into a 10mph wind = 220 yards
# - 100-yard shot into a 20mph wind = 120 yards
# - 200-yard shot into a 20mph wind = 240 yards
# - 100-yard shot into a 30mph wind = 130 yards
# - 200-yard shot into a 30mph wind = 260 yards
# 
# **Wind calculations: Hitting downwind**
# 
# For downwind shots, a common rule of thumb is to subtract approximately half the wind speed in miles per hour from the target yardage. For example, a 10 mph tailwind would result in a reduction of about 5 yards, so judging your distance in the wind would look like this:
# 
# formula = (ws/.5) - yardage
# 
# - 100-yard shot with a 5mph tailwind = 97.5 yards
# - 200-yard shot with a 5mph tailwind = 197.5 yards
# - 100-yard shot with a 10mph tailwind = 95 yards
# - 200-yard shot with a 10mph tailwind = 190 yards
# - 100-yard shot with a 20mph tailwind = 90 yards
# - 200-yard shot with a 20mph tailwind = 180 yards
# - 100-yard shot with a 30mph tailwind = 85 yards
# - 200-yard shot with a 30mph tailwind = 170 
# 
# source: https://www.golfdigest.com/story/wind-formula-mistake-downhead-headwind-effects

# %%
lw_hw0to5 = lw['Carry Distance'].mean()*.05
sw_hw0to5 = sw['Carry Distance'].mean()*.05
gw_hw0to5 = gw['Carry Distance'].mean()*.05
pw_hw0to5 = pw['Carry Distance'].mean()*.05
nineiron_hw0to5 = nine_iron['Carry Distance'].mean()*.05
eightiron_hw0to5 = eight_iron['Carry Distance'].mean()*.05
seveniron_hw0to5 = seven_iron['Carry Distance'].mean()*.05
sixiron_hw0to5 = six_iron['Carry Distance'].mean()*.05
fiveiron_hw0to5 = five_iron['Carry Distance'].mean()*.05
fouriron_hw0to5 = four_iron['Carry Distance'].mean()*.05
threeiron_hw0to5 = three_iron['Carry Distance'].mean()*.05
threehi_hw0to5 = three_hi['Carry Distance'].mean()*.05
threewood_hw0to5 = three_wood['Carry Distance'].mean()*.05
driver_hw0to5 = driver['Carry Distance'].mean()*.05

headwind_0to5 = {
    "0 to 5mph LW": lw_hw0to5,
    "0 to 5mph SW": sw_hw0to5,
    "0 to 5mph GW": gw_hw0to5,
    "0 to 5mph PW": pw_hw0to5,
    "0 to 5mph 9i": nineiron_hw0to5,
    "0 to 5mph 8i": eightiron_hw0to5,
    "0 to 5mph 7i": seveniron_hw0to5,
    "0 to 5mph 6i": sixiron_hw0to5,
    "0 to 5mph 5i": fiveiron_hw0to5,
    "0 to 5mph 4i": fouriron_hw0to5,
    "0 to 5mph 3i": threeiron_hw0to5,
    "0 to 5mph 3hi": threehi_hw0to5,
    "0 to 5mph 3W": threewood_hw0to5,
    "0 to 5mph D": driver_hw0to5
}

print(f"0 to 5 mph headwind yardage effect on each club:")
for label, value in headwind_0to5.items():
    print(f"{label.replace('_', ' ')}: {round(float(value), 2)}")

# %%
lw_hw5to10 = lw['Carry Distance'].mean()*.10
sw_hw5to10 = sw['Carry Distance'].mean()*.10
gw_hw5to10 = gw['Carry Distance'].mean()*.10
pw_hw5to10 = pw['Carry Distance'].mean()*.10
nineiron_hw5to10 = nine_iron['Carry Distance'].mean()*.10
eightiron_hw5to10 = eight_iron['Carry Distance'].mean()*.10
seveniron_hw5to10 = seven_iron['Carry Distance'].mean()*.10
sixiron_hw5to10 = six_iron['Carry Distance'].mean()*.10
fiveiron_hw5to10 = five_iron['Carry Distance'].mean()*.10
fouriron_hw5to10 = four_iron['Carry Distance'].mean()*.10
threeiron_hw5to10 = three_iron['Carry Distance'].mean()*.10
threehi_hw5to10 = three_hi['Carry Distance'].mean()*.10
threewood_hw5to10 = three_wood['Carry Distance'].mean()*.10
driver_hw5to10 = driver['Carry Distance'].mean()*.10

headwind5to10 = {
    "5 to 10mph LW": lw_hw5to10,
    "5 to 10mph SW": sw_hw5to10,
    "5 to 10mph GW": gw_hw5to10,
    "5 to 10mph PW": pw_hw5to10,
    "5 to 10mph 9i": nineiron_hw5to10,
    "5 to 10mph 8i": eightiron_hw5to10,
    "5 to 10mph 7i": seveniron_hw5to10,
    "5 to 10mph 6i": sixiron_hw5to10,
    "5 to 10mph 5i": fiveiron_hw5to10,
    "5 to 10mph 4i": fouriron_hw5to10,
    "5 to 10mph 3i": threeiron_hw5to10,
    "5 to 10mph 3hy": threehi_hw5to10,
    "5 to 10mph 3W": threewood_hw5to10,
    "5 to 10mph D": driver_hw5to10 
}

print(f"5 to 10 mph headwind yardage effect on each club:")
for label, value in headwind5to10.items():
    print(f"{label.replace('_', ' ')}: {round(float(value), 2)}")

# %%
lw_hw10to20 = lw['Carry Distance'].mean()*.20
sw_hw10to20 = sw['Carry Distance'].mean()*.20
gw_hw10to20 = gw['Carry Distance'].mean()*.20
pw_hw10to20 = pw['Carry Distance'].mean()*.20
nineiron_hw10to20 = nine_iron['Carry Distance'].mean()*.20
eightiron_hw10to20 = eight_iron['Carry Distance'].mean()*.20
seveniron_hw10to20 = seven_iron['Carry Distance'].mean()*.20
sixiron_hw10to20 = six_iron['Carry Distance'].mean()*.20
fiveiron_hw10to20 = five_iron['Carry Distance'].mean()*.20
fouriron_hw10to20 = four_iron['Carry Distance'].mean()*.20
threeiron_hw10to20 = three_iron['Carry Distance'].mean()*.20
threehi_hw10to20 = three_hi['Carry Distance'].mean()*.20
threewood_hw10to20 = three_wood['Carry Distance'].mean()*.20
driver_hw10to20 = driver['Carry Distance'].mean()*.20

headwind10to20 = {
    "10 to 20mph LW": lw_hw10to20,
    "10 to 20mph SW": sw_hw10to20,
    "10 to 20mph GW": gw_hw10to20,
    "10 to 20mph PW": pw_hw10to20,
    "10 to 20mph 9i": nineiron_hw10to20,
    "10 to 20mph 8i": eightiron_hw10to20,
    "10 to 20mph 7i": seveniron_hw10to20,
    "10 to 20mph 6i": sixiron_hw10to20,
    "10 to 20mph 5i": fiveiron_hw10to20,
    "10 to 20mph 4i": fouriron_hw10to20,
    "10 to 20mph 3i": threeiron_hw10to20,
    "10 to 20mph 3hy": threehi_hw10to20,
    "10 to 20mph 3W": threewood_hw10to20,
    "10 to 20mph D": driver_hw10to20 
}

print(f"10 to 20 mph headwind yardage effect on each club:")
for label, value in headwind10to20.items():
    print(f"{label.replace('_', ' ')}: {round(float(value), 2)}")

# %%
# Example: 0–5 mph tailwind (using midpoint 5 mph → subtract 2.5 yards)
lw_tw0to5 = lw['Carry Distance'].mean() - (5 / 2)
sw_tw0to5 = sw['Carry Distance'].mean() - (5 / 2)
gw_tw0to5 = gw['Carry Distance'].mean() - (5 / 2)
pw_tw0to5 = pw['Carry Distance'].mean() - (5 / 2)
nineiron_tw0to5 = nine_iron['Carry Distance'].mean() - (5 / 2)
eightiron_tw0to5 = eight_iron['Carry Distance'].mean() - (5 / 2)
seveniron_tw0to5 = seven_iron['Carry Distance'].mean() - (5 / 2)
sixiron_tw0to5 = six_iron['Carry Distance'].mean() - (5 / 2)
fiveiron_tw0to5 = five_iron['Carry Distance'].mean() - (5 / 2)
fouriron_tw0to5 = four_iron['Carry Distance'].mean() - (5 / 2)
threeiron_tw0to5 = three_iron['Carry Distance'].mean() - (5 / 2)
threehi_tw0to5 = three_hi['Carry Distance'].mean() - (5 / 2)
threewood_tw0to5 = three_wood['Carry Distance'].mean() - (5 / 2)
driver_tw0to5 = driver['Carry Distance'].mean() - (5 / 2)

tailwind_0to5 = {
    "0 to 5mph LW": lw_tw0to5,
    "0 to 5mph SW": sw_tw0to5,
    "0 to 5mph GW": gw_tw0to5,
    "0 to 5mph PW": pw_tw0to5,
    "0 to 5mph 9i": nineiron_tw0to5,
    "0 to 5mph 8i": eightiron_tw0to5,
    "0 to 5mph 7i": seveniron_tw0to5,
    "0 to 5mph 6i": sixiron_tw0to5,
    "0 to 5mph 5i": fiveiron_tw0to5,
    "0 to 5mph 4i": fouriron_tw0to5,
    "0 to 5mph 3i": threeiron_tw0to5,
    "0 to 5mph 3hi": threehi_tw0to5,
    "0 to 5mph 3W": threewood_tw0to5,
    "0 to 5mph D": driver_tw0to5
}

print(f"0 to 5 mph tailwind adjusted yardages:")
for label, value in tailwind_0to5.items():
    print(f"{label}: {round(float(value), 2)}")

# %%

# Mean carry per club
carry_per_club = merged_ydg.groupby('Club Type')['Carry Distance'].mean()

# Build output table
club_avgs = pd.DataFrame(index=carry_per_club.index)
club_avgs['Base Carry'] = carry_per_club.round(1)

# Headwind lowers carry
club_avgs['0 to 5 mph headwind']   = (carry_per_club * 0.95).round(1)
club_avgs['5 to 10 mph headwind']  = (carry_per_club * 0.90).round(1)
club_avgs['10 to 20 mph headwind'] = (carry_per_club * 0.80).round(1)
club_avgs['20 to 30 mph headwind'] = (carry_per_club * 0.70).round(1)

# Tailwind increases carry
club_avgs['0 to 5 mph tailwind']   = (carry_per_club * 1.02).round(1)
club_avgs['5 to 10 mph tailwind']  = (carry_per_club * 1.04).round(1)
club_avgs['10 to 20 mph tailwind'] = (carry_per_club * 1.08).round(1)
club_avgs['20 to 30 mph tailwind'] = (carry_per_club * 1.12).round(1)

club_avgs


# %%
club_avgs_order = club_avgs.iloc[[8, 1, 0, 2, 3, 4, 5, 6, 7, 11, 9, 12, 10]]  # Example: Move row 2 to the top, then row 0, then row 1.

# %%
avg_carry_yds.to_csv('/folder/path.data_type')
club_avgs_order.round()


# %%



