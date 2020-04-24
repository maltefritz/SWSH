"""Modifying data to generate heatpump timeseries.

Created on Fri Feb 28 12:09:28 2020

@author: Jonas Freißmann
"""
from os.path import abspath, join

import pandas as pd
import matplotlib.pyplot as plt


# %% Daten einlesen und für Weiterverwendung anpassen
dirpath = abspath(join(__file__, "../.."))
read_path = join(dirpath, "Eingangsdaten",
                 "district-heating-network-data-flensburg-2016.csv")
data = pd.read_csv(read_path)

data['Datetime'] = pd.to_datetime(data['Datetime'], format='%d/%m/%y %H:%M')

col_names = ['Datum', 'T_VL', 'T_RL', 'Last']
data.columns = col_names

data.set_index('Datum', inplace=True)

tvl_list = data['T_VL'].apply(lambda x: int(x)).to_list()


# %% Visualisierung
# Zeitlicher Vorlauftemperaturverlauf
fig, ax = plt.subplots()
plt.plot(data['T_VL'], linewidth=0.5)

ax.set_ylabel('Vorlauftemperatur in °C')
ax.grid(linestyle='--')

plt.show()

# Histogramm der Häufigkeit der Vorlauftemperaturen
fig, ax = plt.subplots()
plt.hist(tvl_list, bins=58)

ax.set_xlabel('Vorlauftemperatur in °C')
ax.set_ylabel('Häufigkeit')
ax.grid(linestyle='--')

plt.show()


# %% TESPy Daten einlesen

read_path = join(dirpath, "Eingangsdaten")

# DH-Wärmepumpe
hpdata = pd.read_csv(join(read_path, "Wärmepumpe_Wasser.csv"), sep=";")
hpdata.set_index('T_DH_VL / C', inplace=True, drop=True)

# LT-Wärmepumpe
lthpdata = pd.read_csv(join(read_path, "LT-Wärmepumpe_Wasser.csv"), sep=";")
lthpdata.set_index('T_DH_VL / C', inplace=True, drop=True)


# % Wertezuweisung nach T_VL-Zeitreihe

# DH-Wärmepumpe
P_max = []
P_min = []
c_1 = []
c_0 = []

for T in tvl_list:
    P_max += [hpdata.loc[T, 'P_max / MW']]
    P_min += [hpdata.loc[T, 'P_min / MW']]
    c_1 += [hpdata.loc[T, 'c_1']]
    c_0 += [hpdata.loc[T, 'c_0']]


# LT-Wärmepumpe
cop_lthp = []

for T in tvl_list:
    cop_lthp += [lthpdata.loc[T, 'COP']]


# % Export in simulation_data.csv

# Import der simulation_data.csv
simdata_path = join(dirpath, "Eingangsdaten\\simulation_data.csv")
simdata = pd.read_csv(simdata_path, sep=";")

# Berechneten Wärmepumpenparameter einfügen
simdata['P_max_hp'] = P_max
simdata['P_min_hp'] = P_min
simdata['c_1_hp'] = c_1
simdata['c_0_hp'] = c_0

simdata['cop_lthp'] = cop_lthp

# Export der simulation_data.csv
simdata.to_csv(simdata_path, sep=";", index=False)
