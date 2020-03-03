"""Preprocessing of weather data for tilted plane.

Created on Wed Jan 22 09:54:59 2020

@author: Malte Fritz und Jonas Freißmann
"""
import os.path as path
import pandas as pd
from ratipl import calculate_radiation


# %% Vorbearbeitung der Eingangsdaten
# Einlesen der Ausgangsdaten des DWD
col_names = ['SID', 'Datum', 'QN', 'AtmoGS', 'Diffus', 'Global', 'SSD',
             'Zenit', 'WOZ', 'eor']
dirpath = path.abspath(path.join(__file__, "../.."))  # Pfad zwei Ebenen höher
read_path = path.join(dirpath, "Eingangsdaten\\strahlung.csv")
data = pd.read_csv(read_path, sep=";", na_values=-999)
data.columns = col_names


# Zeitstempel für Python lesbar/bearbeitbar machen
data['Datum'] = pd.to_datetime(data['Datum'], format='%Y%m%d%H:%M')
data['WOZ'] = pd.to_datetime(data['WOZ'], format='%Y%m%d%H:%M')


# Umrechnen zu gewünschten Einheiten
data['Diffus'] = data['Diffus']/0.36    # J/cm² zu W/m²
data['Global'] = data['Global']/0.36    # J/cm² zu W/m²


# Bestimmen der direkten aus der globalen und diffusen Einstrahlung
data['Direkt'] = data['Global'] - data['Diffus']

# %% Bereitstellen der Einstrahlungsdaten (horizontal)
# Extrahieren des gesuchten Jahres
years = data['WOZ'].apply(lambda x: x.year)
year = 2016    # int(input("Bitte geben Sie das gewünschte Jahr ein: "))
woz_filter = years == year

data_hor = data[['WOZ', 'Global', 'Direkt', 'Diffus']]
data_hor = data_hor[woz_filter]


# Ausgabe der umgeformten horizontalen Einstrahlungsdaten als csv-Datei
write_path1 = path.join(dirpath, "Ergebnisse\\Strahlung_horizontal_"
                        + str(year) + ".csv")
data_hor.to_csv(write_path1, sep=";", na_rep="#N/A")


# %% Bereitstellen der Einstrahlungsdaten (geneigte Ebene)
# Standort Randbedinungen
latitude = 54.78
longitude = 9.43
inclination = 30
south = 0
albedo_val = 0.2


# Umrechnen auf geneigte Ebene
data_gen = calculate_radiation(phi=latitude,
                               lam=longitude,
                               gamma_e=inclination,
                               alpha_e=south,
                               albedo=albedo_val,
                               datetime=data_hor['WOZ'].to_numpy(),
                               e_dir_hor=data_hor['Direkt'].to_numpy(),
                               e_diff_hor=data_hor['Diffus'].to_numpy(),
                               e_g_hor=data_hor['Global'].to_numpy())


# Ausgabe der Ergebnisse als csv-Datei
col_names = ['Datum', 'Global', 'Direkt', 'Diffus', 'Reflekt']
data_gen.columns = col_names
write_path2 = path.join(dirpath, "Ergebnisse\\Strahlung_geneigt_"
                        + str(year) + ".csv")
data_gen.to_csv(write_path2, sep=";", na_rep="#N/A")

# %% Berechnung des Kollektorwärmestroms
# Parameter des Solarkollektors
eta_0 = 0.773  # Alle Parameter aus Solar Keymark vom Arcon-Sunmark A/S Kollek-
a1 = 2.27      # tor HT-SolarBoost 35/10 (siehe "Annahmen Technologieabbildung"
a2 = 0.018     # im Literaturordner der Cloud)

# Einlesen der Temperaturzeitreihen
read_path = path.join(dirpath, "Eingangsdaten\\TempTimeseries2016.csv")
TempData = pd.read_csv(read_path, sep=";", parse_dates=True, index_col='Date')

# Berechnung der Temperaturdifferenz zur Umgebung
T_Kol = (TempData['T_VL'] + TempData['T_RL'])/2
dT = T_Kol - TempData['T_U']

# Berechnung des Kollektorwirkungsgrads und Kollektorwärmestroms
eta = []
Qdot_Kol = []
for i in range(0, len(data_gen['Global'])):
    eta += [eta_0 - (a1*dT.iloc[i])/data_gen.loc[i, 'Global']
            - (a2*dT.iloc[i]**2)/data_gen.loc[i, 'Global']]
    Qdot_Kol += [data_gen.loc[i, 'Global'] * eta[i]]
