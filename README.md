Golf Club Performance – Wind Impact Analysis

This repository contains a Python script, golf_club_performance_by_club.py, that analyzes golf club carry performance and models how headwind and tailwind conditions affect shot distance. All of the data I analyzed I obtained by exporting my Garmin R10 launch monitor data.

The script uses real club data (CSV files) and applies both percentage-based headwind adjustments and simple rule-of-thumb tailwind reductions.

Wind Model Overview

Headwind

Rule of thumb: add +1% to the effective yardage for every 1 mph of headwind.
The ball “plays longer.”

Wind Range	Approx. % Increase	Example (100 yd)
0 – 5 mph	+5 %	105 yd
5 – 10 mph	+10 %	110 yd
10 – 20 mph	+20 %	120 yd
20 – 30 mph	+30 %	130 yd

Tailwind

Rule of thumb: subtract roughly half the wind speed (mph ÷ 2) from the target yardage.
The ball “plays shorter.”

Wind Range	Midpoint (mph)	Subtract (yards)
0 – 5 mph	5 mph	−2.5 yd
5 – 10 mph	7.5 mph	−3.75 yd
10 – 20 mph	15 mph	−7.5 yd
20 – 30 mph	25 mph	−12.5 yd

Input Data

Each input CSV must include these columns:

Column	Description	Example
Club Type	Short name of the club	LW, SW, 7i, 3W, D
Carry Distance	Average carry distance (yards)	135.2

Extra columns are ignored.

How It Works

The script reads all .csv files in your data folder (you set this path in the variable folder_path near the top of the file).

It groups data by Club Type and computes the mean carry per club.

It calculates:

Headwind adjustments (percent increases)

Tailwind adjustments (absolute yardage reductions)

It prints clean, per-club summaries for each wind tier.
