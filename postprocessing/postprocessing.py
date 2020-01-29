"""Module for postprocessing of Solph simulations.

Created on Thu Jan 16 14:23:17 2020

@author: Jonas Freißmann
"""
import os.path as path
import pandas as pd
import matplotlib.pyplot as plt
from invest import npv, LCOH, invest_stes
from znes_plotting import plot as zplt
from znes_plotting import shared


def pp_Ref():
    """Calculate NPV and LCOH and generate plots for Ref system.

    Returns
    -------
    None.
    """
    # Daten einlesen
    dirpath = path.abspath(path.join(__file__, "../.."))
    inv = pd.read_csv(path.join(dirpath,
                                'Ergebnisse\\Ref_Ergebnisse\\Ref_Invest.csv'),
                      sep=";")
    wnw = pd.read_csv(path.join(dirpath,
                                'Ergebnisse\\Ref_Ergebnisse\\Ref_wnw.csv'),
                      sep=";", index_col=0, parse_dates=True)

    invest_ges = float(inv['invest_ges'])
    objective = float(inv['objective'])
    ausgaben = float(inv['ausgaben'])
    total_heat_demand = float(inv['total_heat_demand'])

    # Ergebnisse der Investitionsrechnungen
    netpresentvalue = npv(invest_ges, objective)/1e6
    lcoh = LCOH(invest_ges, ausgaben, total_heat_demand)

    print("Referenzsystem")
    print("Erebnisse der Investitionsrechnungen:")
    print()
    print("Kapitalwert (NPV): " + '{:.3f}'.format(netpresentvalue) + " Mio. €")
    print("Wärmegestehungskosten (LCOH): " + '{:.2f}'.format(lcoh) + " €/MWh")

    # Visualisierung
    ax = zplt.bar(data=wnw.sum(), ylabel='Gesamtwärmemenge in MWh')
    ax.grid(b=False, which='major', axis='x')

    ax = zplt.line(data=wnw, xlabel='Date', ylabel='Wärmeleistung in MW')
    ax.grid(b=False, which='minor', axis='x')

    filename = path.join(dirpath, 'Ergebnisse\\Ref_Ergebnisse\\Ref_plots.pdf')
    shared.create_multipage_pdf(file_name=filename)
    plt.show()


def pp_TES():
    """Calculate NPV and LCOH and generate plots for TES system.

    Returns
    -------
    None.
    """
    # Daten einlesen
    dirpath = path.abspath(path.join(__file__, "../.."))
    inv = pd.read_csv(path.join(dirpath,
                                'Ergebnisse\\TES_Ergebnisse\\TES_Invest.csv'),
                      sep=";")
    wnw = pd.read_csv(path.join(dirpath,
                                'Ergebnisse\\TES_Ergebnisse\\TES_wnw.csv'),
                      sep=";", index_col=0, parse_dates=True)
    tes = pd.read_csv(path.join(
        dirpath, 'Ergebnisse\\TES_Ergebnisse\\TES_Speicher.csv'), sep=";",
        index_col=0, parse_dates=True)

    invest_TES = invest_stes(float(inv['Q_tes']))
    invest_ges = invest_TES + float(inv['invest_ges'])
    objective = float(inv['objective'])
    ausgaben = float(inv['ausgaben'])
    total_heat_demand = float(inv['total_heat_demand'])

    # Ergebnisse der Investitionsrechnungen
    netpresentvalue = npv(invest_ges, objective)/1e6
    lcoh = LCOH(invest_ges, ausgaben, total_heat_demand)

    print("Referenzsystem + Wärmespeicher")
    print("Erebnisse der Investitionsrechnungen:")
    print()
    print("Kapitalwert (NPV): " + '{:.3f}'.format(netpresentvalue) + " Mio. €")
    print("Wärmegestehungskosten (LCOH): " + '{:.2f}'.format(lcoh) + " €/MWh")

    # Visualisierung
    ax = zplt.bar(data=wnw.sum(), ylabel='Gesamtwärmemenge in MWh')
    ax.grid(b=False, which='major', axis='x')

    ax = zplt.line(data=wnw[['BHKW', 'EHK', 'SLK', 'Wärmebedarf']],
                   xlabel='Date', ylabel='Wärmeleistung in MW')
    ax.grid(b=False, which='minor', axis='x')

    ax = zplt.line(data=wnw[['TES Ein', 'TES Aus', 'Wärmebedarf']],
                   xlabel='Date', ylabel='Wärmeleistung in MW')
    ax.grid(b=False, which='minor', axis='x')

    ax = zplt.line(data=tes, xlabel='Date', ylabel='Speicherstand in MWh')
    ax.grid(b=False, which='minor', axis='x')

    filename = path.join(dirpath, 'Ergebnisse\\TES_Ergebnisse\\TES_plots.pdf')
    shared.create_multipage_pdf(file_name=filename)
    plt.show()


def pp_Sol():
    """Calculate NPV and LCOH and generate plots for Sol system.

    Returns
    -------
    None.
    """
    # Daten einlesen
    dirpath = path.abspath(path.join(__file__, "../.."))
    inv = pd.read_csv(path.join(dirpath,
                                'Ergebnisse\\Sol_Ergebnisse\\Sol_Invest.csv'),
                      sep=";")
    wnw = pd.read_csv(path.join(dirpath,
                                'Ergebnisse\\Sol_Ergebnisse\\Sol_wnw.csv'),
                      sep=";", index_col=0, parse_dates=True)
    tes = pd.read_csv(path.join(
        dirpath, 'Ergebnisse\\Sol_Ergebnisse\\Sol_Speicher.csv'), sep=";",
        index_col=0, parse_dates=True)

    invest_TES = invest_stes(float(inv['Q_tes']))
    invest_ges = invest_TES + float(inv['invest_ges'])
    objective = float(inv['objective'])
    ausgaben = float(inv['ausgaben'])
    total_heat_demand = float(inv['total_heat_demand'])

    # Ergebnisse der Investitionsrechnungen
    netpresentvalue = npv(invest_ges, objective)/1e6
    lcoh = LCOH(invest_ges, ausgaben, total_heat_demand)

    print("Referenzsystem + Wärmespeicher + Solarthermie")
    print("Erebnisse der Investitionsrechnungen:")
    print()
    print("Kapitalwert (NPV): " + '{:.3f}'.format(netpresentvalue) + " Mio. €")
    print("Wärmegestehungskosten (LCOH): " + '{:.2f}'.format(lcoh) + " €/MWh")

    # Visualisierung
    ax = zplt.bar(data=wnw.sum(), ylabel='Gesamtwärmemenge in MWh')
    ax.grid(b=False, which='major', axis='x')

    ax = zplt.line(data=wnw, xlabel='Date', ylabel='Wärmeleistung in MW')
    ax.grid(b=False, which='minor', axis='x')

    ax = zplt.line(data=wnw[['BHKW', 'EHK', 'SLK', 'Wärmebedarf']],
                   xlabel='Date', ylabel='Wärmeleistung in MW')
    ax.grid(b=False, which='minor', axis='x')

    ax = zplt.line(data=wnw[['TES Ein', 'TES Aus', 'Wärmebedarf']],
                   xlabel='Date', ylabel='Wärmeleistung in MW')
    ax.grid(b=False, which='minor', axis='x')

    ax = zplt.line(data=tes, xlabel='Date', ylabel='Speicherstand in MWh')
    ax.grid(b=False, which='minor', axis='x')

    ax = zplt.line(data=wnw[['Solar', 'Wärmebedarf']], xlabel='Date',
                   ylabel='Wärmeleistung in MW')
    ax.grid(b=False, which='minor', axis='x')

    filename = path.join(dirpath, 'Ergebnisse\\Sol_Ergebnisse\\Sol_plots.pdf')
    shared.create_multipage_pdf(file_name=filename)
    plt.show()
