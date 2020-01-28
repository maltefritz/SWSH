# -*- coding: utf-8 -*-
"""
Created on Wed Jan 22 09:48:39 2020

@author: Malte Fritz

Es werden die Wetterdaten des DWDs aufgerufen und auf das für oemof.solph
benötigte Format angepasst.
"""

import pandas as pd
import numpy as np
from ratipl import calculate_radiation as cr

#%% Strahlung auf horizontaler Kollektorfläche

# Gewünschtes Jahr auswählen
# a = int(input('Gib das Jahr an, von dem du die Wetterdaten haben möchtest: '))
a = 2016

# Datensatz lesbar machen
col_names = ['SID', 'Datum', 'QN', 'Atmo_GS', 'Diffus', 'Global', 'SSD', 'Zenit', 'WOZ', 'eor']
data = pd.read_csv('strahlung.csv', sep=';', na_values=-999)
data.columns = col_names

# Daten anpassen
data['Datum'] = pd.to_datetime(data['Datum'], format='%Y%m%d%H:%M')
data['WOZ'] = pd.to_datetime(data['WOZ'], format='%Y%m%d%H:%M')

# Einheiten umwandeln J/cm² -> W/m²
data['Diffus'] = data['Diffus']/0.36
data['Global'] = data['Global']/0.36

# Direkte Strahlung berechnen
data['Direkt'] = data['Global'] - data['Diffus']

# Daten filtern
years = data['WOZ'].apply(lambda x: x.year)
woz_filter = years == a

# Datensatz der horizontalen Strahlung erstellen
data_hor = data[['WOZ', 'Global', 'Direkt', 'Diffus']]
data_hor = data_hor[woz_filter]
data_hor.to_csv('Strahlung_horizontal_' + str(a) + '.csv', sep=';', na_rep='#N/A')

#%% Strahlung auf der geneigten Kollektorfläche

# Auslegung des Kollektors für FL:

latitude = 54.78
longitude = 9.43
inclination = 30
south = 0
albedo_val = 0.2

total_radiation = []

for inclination in range(30,60):
    data_gen = cr(phi=latitude, lam=longitude, gamma_e=inclination, 
              alpha_e=south, albedo=albedo_val, 
              datetime=data_hor['WOZ'].to_numpy(), 
              e_dir_hor=data_hor['Direkt'].to_numpy(), 
              e_diff_hor=data_hor['Diffus'].to_numpy(), 
              e_g_hor=data_hor['Global'].to_numpy())
    
    total_radiation += [data_gen["global"].sum()]
    print("Einstrahlung auf die geneigte Ebene ({}°): ".format(inclination) + str(data_gen["global"].sum()) + " Wh/(m²a)")


# Datensatz der geneigte Strahlung erstellen
# data_gen = data[['WOZ', 'Global', 'Direkt', 'Diffus', 'Reflekt']]
data_gen.to_csv('Strahlung_geneigt_' + str(a) + '.csv', sep=';', na_rep='#N/A')

col_name = ['Datum', 'Global', 'Direkt', 'Diffus', 'Reflekt']
data_gen = pd.read_csv('Strahlung_horizontal_' + str(a) + '.csv', sep=';', na_values=-999)
data_gen.columns = col_name

data_gen.to_csv('Strahlung_geneigt_' + str(a) + '.csv', sep=';', na_rep='#N/A')