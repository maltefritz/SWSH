"""Module for postprocessing of SWSH's Solph simulations.

Created on Thu Jan 16 14:23:17 2020

@author: Jonas Freißmann
"""
import os.path as path
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from invest import npv, LCOH, invest_stes
from znes_plotting import plot as zplt
from znes_plotting import shared


def pp_Ref():
    """Calculate NPV and LCOH and generate plots for Ref system.

    Returns
    -------
    None.
    """
    # %% Daten einlesen

    dirpath = path.abspath(path.join(__file__, "../.."))

    # Invest
    inv = pd.read_csv(path.join(dirpath,
                                'Ergebnisse\\Ref_Ergebnisse\\Ref_Invest.csv'),
                      sep=";")

    invest_ges = float(inv['invest_ges'])
    objective = float(inv['objective'])
    ausgaben = float(inv['ausgaben'])
    total_heat_demand = float(inv['total_heat_demand'])

    # CO2
    use = pd.read_csv(path.join(dirpath,
                                'Ergebnisse\\Ref_Ergebnisse\\Ref_CO2.csv'),
                      sep=";", index_col=0, parse_dates=True)

    co2 = pd.read_csv('emissions2016.csv', sep=";", index_col=0,
                      parse_dates=True)

    Em_om = []
    Em_dm = []

    e_fuel = 0.2012    # in t/MWh aus "Emissionsbewertung Daten"

    # Ergebnisvisualisierung
    wnw = pd.read_csv(path.join(dirpath,
                                'Ergebnisse\\Ref_Ergebnisse\\Ref_wnw.csv'),
                      sep=";", index_col=0, parse_dates=True)

    # %% Ergebnisse der Investitionsrechnungen
    netpresentvalue = npv(invest_ges, objective)/1e6
    lcoh = LCOH(invest_ges, ausgaben, total_heat_demand)

    print("Referenzsystem")
    print()
    print("Erebnisse der Investitionsrechnungen:")
    print()
    print("Kapitalwert (NPV): " + '{:.3f}'.format(netpresentvalue) + " Mio. €")
    print("Wärmegestehungskosten (LCOH): " + '{:.2f}'.format(lcoh) + " €/MWh")

    # %% Ergebnisse der Emissionsrechnung
    for idx in range(0, len(use)):
        OM = ((use.iloc[idx, 0] + use.iloc[idx, 1]) * e_fuel
              + use.iloc[idx, 3] * co2.iloc[idx, 0]
              - use.iloc[idx, 2] * co2.iloc[idx, 0])

        DM = ((use.iloc[idx, 0] + use.iloc[idx, 1]) * e_fuel
              + use.iloc[idx, 3] * co2.iloc[idx, 1]
              - use.iloc[idx, 2] * co2.iloc[idx, 1])

        Em_om.append(OM)
        Em_dm.append(DM)

    totEm_om = sum(Em_om)
    totEm_dm = sum(Em_dm)

    dfEm = pd.DataFrame({'Gesamtmix': [totEm_om],
                         'Verdrängungsmix': [totEm_dm]})

    print()
    print("Erebnisse der Emissionsrechnungen:")
    print()
    print("Gesamtemissionen (Gesamtmix): " + '{:.0f}'.format(totEm_om)
          + " t CO2")
    print("Gesamtemissionen (Verdrängungsmix): " + '{:.0f}'.format(totEm_dm)
          + " t CO2")

    # %% Visualisierung
    ax = zplt.bar(data=wnw.sum(), ylabel='Gesamtwärmemenge in MWh')
    ax.grid(b=False, which='major', axis='x')

    ax = zplt.line(data=wnw, xlabel='Date', ylabel='Wärmeleistung in MW',
                   drawstyle='steps-mid')
    ax.grid(b=False, which='minor', axis='x')

    ax = zplt.bar(data=dfEm.transpose().loc[:, 0],
                  ylabel='CO2-Emissionen in t')
    ax.grid(b=False, which='major', axis='x')

    # 7-Tage Plots
    idx = pd.date_range('2016-04-04 00:00:00', '2016-04-10 0:00:00', freq='h')

    ax = zplt.line(data=wnw.loc[idx, :], xlabel='Date',
                   ylabel='Wärmeleistung in MW', drawstyle='steps-mid')

    filename = path.join(dirpath, 'Ergebnisse\\Ref_Ergebnisse\\Ref_plots.pdf')
    shared.create_multipage_pdf(file_name=filename)
    plt.show()


def pp_TES():
    """Calculate NPV and LCOH and generate plots for TES system.

    Returns
    -------
    None.
    """
    # %% Daten einlesen

    dirpath = path.abspath(path.join(__file__, "../.."))

    # Invest
    inv = pd.read_csv(path.join(dirpath,
                                'Ergebnisse\\TES_Ergebnisse\\TES_Invest.csv'),
                      sep=";")

    invest_TES = invest_stes(float(inv['Q_tes']))
    invest_ges = invest_TES + float(inv['invest_ges'])
    objective = float(inv['objective'])
    ausgaben = float(inv['ausgaben'])
    total_heat_demand = float(inv['total_heat_demand'])

    # CO2
    use = pd.read_csv(path.join(dirpath,
                                'Ergebnisse\\TES_Ergebnisse\\TES_CO2.csv'),
                      sep=";", index_col=0, parse_dates=True)

    co2 = pd.read_csv('emissions2016.csv', sep=";", index_col=0,
                      parse_dates=True)

    Em_om = []
    Em_dm = []

    e_fuel = 0.2012    # in t/MWh aus "Emissionsbewertung Daten"

    # Ergebnisvisualisierung
    wnw = pd.read_csv(path.join(dirpath,
                                'Ergebnisse\\TES_Ergebnisse\\TES_wnw.csv'),
                      sep=";", index_col=0, parse_dates=True)
    tes = pd.read_csv(path.join(
        dirpath, 'Ergebnisse\\TES_Ergebnisse\\TES_Speicher.csv'), sep=";",
        index_col=0, parse_dates=True)

    # %% Ergebnisse der Investitionsrechnungen
    netpresentvalue = npv(invest_ges, objective)/1e6
    lcoh = LCOH(invest_ges, ausgaben, total_heat_demand)

    print("Referenzsystem + Wärmespeicher")
    print()
    print("Erebnisse der Investitionsrechnungen:")
    print()
    print("Kapitalwert (NPV): " + '{:.3f}'.format(netpresentvalue) + " Mio. €")
    print("Wärmegestehungskosten (LCOH): " + '{:.2f}'.format(lcoh) + " €/MWh")

    # %% Ergebnisse der Emissionsrechnung
    for idx in range(0, len(use)):
        OM = ((use.iloc[idx, 0] + use.iloc[idx, 1]) * e_fuel
              + use.iloc[idx, 3] * co2.iloc[idx, 0]
              - use.iloc[idx, 2] * co2.iloc[idx, 0])

        DM = ((use.iloc[idx, 0] + use.iloc[idx, 1]) * e_fuel
              + use.iloc[idx, 3] * co2.iloc[idx, 1]
              - use.iloc[idx, 2] * co2.iloc[idx, 1])

        Em_om.append(OM)
        Em_dm.append(DM)

    totEm_om = sum(Em_om)
    totEm_dm = sum(Em_dm)

    dfEm = pd.DataFrame({'Gesamtmix': [totEm_om],
                         'Verdrängungsmix': [totEm_dm]})

    print()
    print("Erebnisse der Emissionsrechnungen:")
    print()
    print("Gesamtemissionen (Gesamtmix): " + '{:.0f}'.format(totEm_om)
          + " t CO2")
    print("Gesamtemissionen (Verdrängungsmix): " + '{:.0f}'.format(totEm_dm)
          + " t CO2")

    # %% Visualisierung
    ax = zplt.bar(data=wnw.sum(), ylabel='Gesamtwärmemenge in MWh')
    ax.grid(b=False, which='major', axis='x')

    ax = zplt.line(data=wnw[['BHKW', 'EHK', 'SLK', 'Wärmebedarf']],
                   xlabel='Date', ylabel='Wärmeleistung in MW',
                   drawstyle='steps-mid')
    ax.grid(b=False, which='minor', axis='x')

    ax = zplt.line(data=wnw[['TES Ein', 'TES Aus', 'Wärmebedarf']],
                   xlabel='Date', ylabel='Wärmeleistung in MW',
                   drawstyle='steps-mid')
    ax.grid(b=False, which='minor', axis='x')

    ax = zplt.line(data=tes, xlabel='Date', ylabel='Speicherstand in MWh',
                   drawstyle='steps-mid')
    ax.grid(b=False, which='minor', axis='x')

    ax = zplt.bar(data=dfEm.transpose().loc[:, 0],
                  ylabel='CO2-Emissionen in t')
    ax.grid(b=False, which='major', axis='x')

    # 7-Tage Plots
    idx = pd.date_range('2016-04-04 00:00:00', '2016-04-10 0:00:00', freq='h')

    ax = zplt.line(data=wnw.loc[idx, ['BHKW', 'EHK', 'SLK', 'Wärmebedarf']],
                   xlabel='Date', ylabel='Wärmeleistung in MW',
                   drawstyle='steps-mid')

    ax = zplt.line(data=wnw.loc[idx, ['TES Ein', 'TES Aus', 'Wärmebedarf']],
                   xlabel='Date', ylabel='Wärmeleistung in MW',
                   drawstyle='steps-mid')

    ax = zplt.line(data=tes.loc[idx, :], xlabel='Date',
                   ylabel='Speicherstand in MWh', drawstyle='steps-mid')

    filename = path.join(dirpath, 'Ergebnisse\\TES_Ergebnisse\\TES_plots.pdf')
    shared.create_multipage_pdf(file_name=filename)
    plt.show()


def pp_Sol():
    """Calculate NPV and LCOH and generate plots for Sol system.

    Returns
    -------
    None.
    """
    # %% Daten einlesen

    dirpath = path.abspath(path.join(__file__, "../.."))

    # Invest
    inv = pd.read_csv(path.join(dirpath,
                                'Ergebnisse\\Sol_Ergebnisse\\Sol_Invest.csv'),
                      sep=";")

    invest_TES = invest_stes(float(inv['Q_tes']))
    invest_ges = invest_TES + float(inv['invest_ges'])
    objective = float(inv['objective'])
    ausgaben = float(inv['ausgaben'])
    total_heat_demand = float(inv['total_heat_demand'])

    # CO2
    use = pd.read_csv(path.join(dirpath,
                                'Ergebnisse\\Sol_Ergebnisse\\Sol_CO2.csv'),
                      sep=";", index_col=0, parse_dates=True)

    co2 = pd.read_csv('emissions2016.csv', sep=";", index_col=0,
                      parse_dates=True)

    Em_om = []
    Em_dm = []

    e_fuel = 0.2012    # in t/MWh aus "Emissionsbewertung Daten"

    # Ergebnisvisualisierung
    wnw = pd.read_csv(path.join(dirpath,
                                'Ergebnisse\\Sol_Ergebnisse\\Sol_wnw.csv'),
                      sep=";", index_col=0, parse_dates=True)
    tes = pd.read_csv(path.join(
        dirpath, 'Ergebnisse\\Sol_Ergebnisse\\Sol_Speicher.csv'), sep=";",
        index_col=0, parse_dates=True)

    # %% Ergebnisse der Investitionsrechnungen
    netpresentvalue = npv(invest_ges, objective)/1e6
    lcoh = LCOH(invest_ges, ausgaben, total_heat_demand)

    print("Referenzsystem + Wärmespeicher + Solarthermie")
    print()
    print("Erebnisse der Investitionsrechnungen:")
    print()
    print("Kapitalwert (NPV): " + '{:.3f}'.format(netpresentvalue) + " Mio. €")
    print("Wärmegestehungskosten (LCOH): " + '{:.2f}'.format(lcoh) + " €/MWh")

    # %% Ergebnisse der Emissionsrechnung
    for idx in range(0, len(use)):
        OM = ((use.iloc[idx, 0] + use.iloc[idx, 1]) * e_fuel
              + use.iloc[idx, 3] * co2.iloc[idx, 0]
              - use.iloc[idx, 2] * co2.iloc[idx, 0])

        DM = ((use.iloc[idx, 0] + use.iloc[idx, 1]) * e_fuel
              + use.iloc[idx, 3] * co2.iloc[idx, 1]
              - use.iloc[idx, 2] * co2.iloc[idx, 1])

        Em_om.append(OM)
        Em_dm.append(DM)

    totEm_om = sum(Em_om)
    totEm_dm = sum(Em_dm)

    dfEm = pd.DataFrame({'Gesamtmix': [totEm_om],
                         'Verdrängungsmix': [totEm_dm]})

    print()
    print("Erebnisse der Emissionsrechnungen:")
    print()
    print("Gesamtemissionen (Gesamtmix): " + '{:.0f}'.format(totEm_om)
          + " t CO2")
    print("Gesamtemissionen (Verdrängungsmix): " + '{:.0f}'.format(totEm_dm)
          + " t CO2")

    # %% Visualisierung
    ax = zplt.bar(data=wnw.sum(), ylabel='Gesamtwärmemenge in MWh')
    ax.grid(b=False, which='major', axis='x')

    ax = zplt.line(data=wnw, xlabel='Date', ylabel='Wärmeleistung in MW',
                   drawstyle='steps-mid')
    ax.grid(b=False, which='minor', axis='x')

    ax = zplt.line(data=wnw[['BHKW', 'EHK', 'SLK', 'Wärmebedarf']],
                   xlabel='Date', ylabel='Wärmeleistung in MW',
                   drawstyle='steps-mid')
    ax.grid(b=False, which='minor', axis='x')

    ax = zplt.line(data=wnw[['TES Ein', 'TES Aus', 'Wärmebedarf']],
                   xlabel='Date', ylabel='Wärmeleistung in MW',
                   drawstyle='steps-mid')
    ax.grid(b=False, which='minor', axis='x')

    ax = zplt.line(data=tes, xlabel='Date', ylabel='Speicherstand in MWh',
                   drawstyle='steps-mid')
    ax.grid(b=False, which='minor', axis='x')

    ax = zplt.line(data=wnw[['Solar', 'Wärmebedarf']], xlabel='Date',
                   ylabel='Wärmeleistung in MW', drawstyle='steps-mid')
    ax.grid(b=False, which='minor', axis='x')

    ax = zplt.bar(data=dfEm.transpose().loc[:, 0],
                  ylabel='CO2-Emissionen in t')
    ax.grid(b=False, which='major', axis='x')

    # 7-Tage Plots
    idx = pd.date_range('2016-04-04 00:00:00', '2016-04-10 0:00:00', freq='h')

    ax = zplt.line(data=wnw.loc[idx, ['BHKW', 'EHK', 'SLK', 'Wärmebedarf']],
                   xlabel='Date', ylabel='Wärmeleistung in MW',
                   drawstyle='steps-mid')

    ax = zplt.line(data=wnw.loc[idx, ['TES Ein', 'TES Aus', 'Wärmebedarf']],
                   xlabel='Date', ylabel='Wärmeleistung in MW',
                   drawstyle='steps-mid')

    ax = zplt.line(data=tes.loc[idx, :], xlabel='Date',
                   ylabel='Speicherstand in MWh', drawstyle='steps-mid')

    ax = zplt.line(data=wnw.loc[idx, ['Solar', 'Wärmebedarf']], xlabel='Date',
                   ylabel='Wärmeleistung in MW', drawstyle='steps-mid')

    filename = path.join(dirpath, 'Ergebnisse\\Sol_Ergebnisse\\Sol_plots.pdf')
    shared.create_multipage_pdf(file_name=filename)
    plt.show()


def pp_Vorarbeit():
    """Calculate NPV and LCOH and generate plots for Vorarbeit system.

    Returns
    -------
    None.
    """
    # %% Daten einlesen

    dirpath = path.abspath(
        path.join(__file__, "../..", "Ergebnisse\\Vorarbeit"))

    # Invest
    inv = pd.read_csv(path.join(dirpath, 'Vor_Invest.csv'), sep=";")

    invest_TES = invest_stes(float(inv['Q_tes']))
    invest_ges = invest_TES + float(inv['invest_ges'])
    Gesamtbetrag = float(inv['Gesamtbetrag'])
    total_heat_demand = float(inv['total_heat_demand'])

    # CO2
    use = pd.read_csv(path.join(dirpath, 'Vor_CO2.csv'),
                      sep=";", index_col=0, parse_dates=True)

    co2 = pd.read_csv('emissions2016.csv', sep=";", index_col=0,
                      parse_dates=True)

    znescolors = {
        'darkblue': '#00395B',
        'red': '#B54036',
        'lightblue': '#74ADC0',
        'orange': '#EC6707',
        'grey': '#BFBFBF',
        'dimgrey': 'dimgrey',
        'lightgrey': 'lightgrey',
        'slategrey': 'slategrey',
        'darkgrey': '#A9A9A9'
    }

    Em_om = []
    Em_dm = []

    e_fuel = 0.2012    # in t/MWh aus "Emissionsbewertung Daten"

    # Ergebnisvisualisierung
    wnw = pd.read_csv(path.join(dirpath, 'Vor_wnw.csv'),
                      sep=";", index_col=0, parse_dates=True)

    dauerlinie = wnw.apply(lambda x: x.sort_values(ascending=False).values)
    dauerlinie.reset_index(drop=True, inplace=True)

    # %% Ergebnisse der Investitionsrechnungen
    npv_result = npv(invest_ges, Gesamtbetrag)/1e6
    lcoh = LCOH(invest_ges, Gesamtbetrag, total_heat_demand)

    print("GuD, BHKW, SLK, WP, EHK, STES & Solar")
    print()
    print("Erebnisse der Investitionsrechnungen:")
    print()
    print("Kapitalwert (NPV): " + '{:.3f}'.format(npv_result) + " Mio. €")
    print("Wärmegestehungskosten (LCOH): " + '{:.2f}'.format(lcoh) + " €/MWh")

    # %% Ergebnisse der Emissionsrechnung
    for idx in range(0, len(use)):
        OM = (use.iloc[idx, 0] * e_fuel
              + use.iloc[idx, 2] * co2.iloc[idx, 0]
              - use.iloc[idx, 1] * co2.iloc[idx, 0])

        DM = (use.iloc[idx, 0] * e_fuel
              + use.iloc[idx, 2] * co2.iloc[idx, 1]
              - use.iloc[idx, 1] * co2.iloc[idx, 1])

        Em_om.append(OM)
        Em_dm.append(DM)

    totEm_om = sum(Em_om)
    totEm_dm = sum(Em_dm)

    dfEm = pd.DataFrame({'Gesamtmix': [totEm_om],
                         'Verdrängungsmix': [totEm_dm]})

    print()
    print("Erebnisse der Emissionsrechnungen:")
    print()
    print("Gesamtemissionen (Gesamtmix): " + '{:.0f}'.format(totEm_om)
          + " t CO2")
    print("Gesamtemissionen (Verdrängungsmix): " + '{:.0f}'.format(totEm_dm)
          + " t CO2")

    # %% Visualisierung
    ax = zplt.area(data=wnw[['GuD', 'BHKW', 'SLK', 'EHK', 'WP', 'Solar']],
                   xlabel='Datum', ylabel='Wärmeleistung in MW')

    fig, ax = plt.subplots()

    zplt.scatter(data=wnw, xlabel='Wärmestrom Q in MW', x='BHKW',
                 ylabel='Elektrische Leistung P in MW', y='P_BHKW',
                 color=znescolors['darkblue'], ax=ax)

    zplt.scatter(data=wnw, xlabel='Wärmestrom Q in MW', x='GuD',
                 ylabel='Elektrische Leistung P in MW', y='P_GuD',
                 color=znescolors['red'], ax=ax)
    ax.legend(['BHKW', 'GuD'])

    # ax = zplt.scatter(data=wnw, xlabel='Wärmestrom Q in MW', x='GuD',
    #                   ylabel='El. Leistung P in MW', y='P_GuD')

    # Balkendiagramm Gesamtwärmemengen aller Technologien
    plt.figure()
    ax = zplt.bar(data=wnw[['GuD', 'BHKW', 'SLK', 'EHK', 'WP', 'LT-WP ab',
                            'LT-WP zu', 'Solar']].sum(),
                  ylabel='Gesamtwärmemenge in MWh')
    ax.grid(b=False, which='major', axis='x')

    plt.figure()
    label = ['GuD', 'BHKW', 'SLK', 'EHK', 'WP', 'Solar']
    ax = plt.pie(wnw[['GuD', 'BHKW', 'SLK', 'EHK', 'WP', 'Solar']].sum()
                 / wnw['Bedarf'].sum(),
                 labels=label,
                 colors=shared.znes_colors(n=6),
                 autopct='%.2f%%')

    # Jahresdauerlinien aller Technologien
    ax = zplt.line(data=dauerlinie[['GuD', 'BHKW', 'SLK', 'EHK', 'WP',
                                    'LT-WP ab', 'Solar']],
                   xlabel='Stunden', ylabel='Wärmeleistung in MW',
                   drawstyle='steps-mid')
    ax.grid(b=False, which='minor', axis='x')

    # Jahresdauerlinien aller Technologien ohne LT-HP
    ax = zplt.line(data=dauerlinie[['GuD', 'BHKW', 'SLK', 'EHK', 'WP',
                                    'Solar']],
                   xlabel='Stunden', ylabel='Wärmeleistung in MW',
                   drawstyle='steps-mid')
    ax.grid(b=False, which='minor', axis='x')

    # Jahresdauerlinie des TES
    ax = zplt.line(data=dauerlinie[['TES Ein', 'TES Aus']],
                   xlabel='Stunden', ylabel='Wärmeleistung in MW',
                   drawstyle='steps-mid')
    ax.grid(b=False, which='minor', axis='x')

    # # Jahresverlauf aller Technologien + TES + Bedarf
    # ax = zplt.line(data=wnw, xlabel='Date', ylabel='Wärmeleistung in MW',
    #                drawstyle='steps-mid')
    # ax.grid(b=False, which='minor', axis='x')

    # Jahresverlauf aller Technologien einzeln
    ax = zplt.line(data=wnw[['BHKW', 'Bedarf']],
                   xlabel='Datum', ylabel='Wärmeleistung in MW',
                   drawstyle='steps-mid')
    ax.grid(b=False, which='minor', axis='x')

    ax = zplt.line(data=wnw[['EHK', 'Bedarf']],
                   xlabel='Datum', ylabel='Wärmeleistung in MW',
                   drawstyle='steps-mid')
    ax.grid(b=False, which='minor', axis='x')

    ax = zplt.line(data=wnw[['GuD', 'Bedarf']],
                   xlabel='Datum', ylabel='Wärmeleistung in MW',
                   drawstyle='steps-mid')
    ax.grid(b=False, which='minor', axis='x')

    ax = zplt.line(data=wnw[['SLK', 'Bedarf']],
                   xlabel='Datum', ylabel='Wärmeleistung in MW',
                   drawstyle='steps-mid')
    ax.grid(b=False, which='minor', axis='x')

    ax = zplt.line(data=wnw[['WP', 'Bedarf']],
                   xlabel='Datum', ylabel='Wärmeleistung in MW',
                   drawstyle='steps-mid')
    ax.grid(b=False, which='minor', axis='x')

    ax = zplt.line(data=wnw[['LT-WP ab', 'Bedarf']],
                   xlabel='Datum', ylabel='Wärmeleistung in MW',
                   drawstyle='steps-mid')
    ax.grid(b=False, which='minor', axis='x')

    ax = zplt.line(data=wnw[['Solar', 'Bedarf']],
                   xlabel='Datum', ylabel='Wärmeleistung in MW',
                   drawstyle='steps-mid')
    ax.grid(b=False, which='minor', axis='x')

    ax = zplt.line(data=wnw[['TES Ein', 'TES Aus', 'Bedarf']],
                   xlabel='Datum', ylabel='Wärmeleistung in MW',
                   drawstyle='steps-mid')
    ax.grid(b=False, which='minor', axis='x')

    # Jahresverlauf des Speicherstands
    ax = zplt.line(data=wnw[['Speicherstand']],
                   xlabel='Datum', ylabel='Speicherstand in MWh',
                   drawstyle='steps-mid')
    ax.grid(b=False, which='minor', axis='x')
    ax.get_legend().remove()

    # CO2-Emissionen
    plt.figure()
    ax = zplt.bar(data=dfEm.transpose().loc[:, 0],
                  ylabel='CO2-Emissionen in t')
    ax.grid(b=False, which='major', axis='x')
    # ax.get_legend().remove()

    # 7-Tage Plots
    idx = pd.date_range('2016-04-04 00:00:00', '2016-04-10 0:00:00', freq='h')

    ax = zplt.area(data=wnw.loc[idx, ['GuD', 'BHKW', 'SLK', 'EHK', 'WP',
                                      'Solar']],
                   xlabel='Datum', ylabel='Wärmeleistung in MW')
    ax.legend(loc='upper right')

    ax = zplt.line(data=wnw.loc[idx, ['GuD', 'BHKW', 'SLK', 'EHK', 'WP',
                                      'LT-WP ab', 'Bedarf']],
                   xlabel='Datum', ylabel='Wärmeleistung in MW',
                   drawstyle='steps-mid')

    ax = zplt.line(data=wnw.loc[idx, ['TES Ein', 'TES Aus', 'Bedarf']],
                   xlabel='Datum', ylabel='Wärmeleistung in MW',
                   drawstyle='steps-mid')

    ax = zplt.line(data=wnw.loc[idx, ['Speicherstand']], xlabel='Datum',
                   ylabel='Speicherstand in MWh', drawstyle='steps-mid')
    ax.get_legend().remove()

    ax = zplt.line(data=wnw.loc[idx, ['Solar', 'Bedarf']], xlabel='Datum',
                   ylabel='Wärmeleistung in MW', drawstyle='steps-mid')

    filename = path.join(dirpath, 'Vor_plots.pdf')
    shared.create_multipage_pdf(file_name=filename)
    plt.show()


def run_all():
    """Run postprocessing for all modells."""
    print('Ref_Land:')
    pp_Ref()
    print('####################')
    print()
    print('TES_Land:')
    pp_TES()
    print('####################')
    print()
    print('Sol_Land:')
    pp_Sol()
    print('####################')

dirpath = path.abspath(
        path.join(__file__, "../..", "Ergebnisse\\Vorarbeit"))
wnw = pd.read_csv(path.join(dirpath, 'Vor_wnw.csv'),
                      sep=";", index_col=0, parse_dates=True)
