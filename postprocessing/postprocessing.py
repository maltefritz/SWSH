# -*- coding: utf-8 -*-
"""
Created on Thu Jan 16 14:23:17 2020

@author: Jonas Freißmann
"""

import pandas as pd
import matplotlib.pyplot as plt
from invest import npv, LCOH, invest_stes
from znes_plotting import plot as zplt
from znes_plotting import shared

def pp_Ref():
    #%% Daten einlesen
    inv = pd.read_csv('Invest.csv', sep=";")
    
    wnw = pd.read_csv('Ergebnis.csv', sep=";", index_col=0, parse_dates=True)
    
    
    #%% Ergebnisse der Investitionsrechnungen
    print("Referenzsystem")
    print("Erebnisse der Investitionsrechnungen:")
    print()
    
    netpresentvalue = npv(float(inv['invest_ges']), float(inv['objective']))/1e6
    print("Kapitalwert (NPV): " + '{:.3f}'.format(netpresentvalue) + " Mio. €")
    
    lcoh = LCOH(float(inv['invest_ges']), float(inv['ausgaben']), 
                float(inv['total_heat_demand']))
    print("Wärmegestehungskosten (LCOH): " + '{:.2f}'.format(lcoh) + " €/MWh")
    
    
    #%% Visualisierung
    ax = zplt.bar(data=wnw.sum(), ylabel='Gesamtwärmemenge in MWh')
    ax.grid(b=False, which='major', axis='x')
    
    ax = zplt.line(data=wnw, xlabel='Date', ylabel='Wärmeleistung in MW')
    ax.grid(b=False, which='minor', axis='x')
    
    shared.create_multipage_pdf()
    plt.show()


def pp_RefTES():
    #%% Daten einlesen
    inv = pd.read_csv('InvestTES.csv', sep=";")
    
    wnw = pd.read_csv('ErgebnisTES.csv', sep=";", index_col=0, parse_dates=True)
    
    
    #%% Ergebnisse der Investitionsrechnungen
    invest_TES = invest_stes(float(inv['Q_tes']))
    invest_ges = invest_TES + float(inv['invest_ges'])
    
    print("Referenzsystem + Wärmespeicher")
    print("Erebnisse der Investitionsrechnungen:")
    print()
    
    netpresentvalue = npv(invest_ges, float(inv['objective']))/1e6
    print("Kapitalwert (NPV): " + '{:.3f}'.format(netpresentvalue) + " Mio. €")
    
    lcoh = LCOH(invest_ges, float(inv['ausgaben']), 
                float(inv['total_heat_demand']))
    print("Wärmegestehungskosten (LCOH): " + '{:.2f}'.format(lcoh) + " €/MWh")
    
    
    #%% Visualisierung
    ax = zplt.bar(data=wnw.sum(), ylabel='Gesamtwärmemenge in MWh')
    ax.grid(b=False, which='major', axis='x')
    
    ax = zplt.line(data=wnw[['BHKW', 'EHK', 'SLK', 'Wärmebedarf']], xlabel='Date', ylabel='Wärmeleistung in MW')
    ax.grid(b=False, which='minor', axis='x')
    
    ax = zplt.line(data=wnw[['TES Ein', 'TES Aus', 'Wärmebedarf']], xlabel='Date', ylabel='Wärmeleistung in MW')
    ax.grid(b=False, which='minor', axis='x')
    
    shared.create_multipage_pdf(file_name='plotsTES.pdf')
    plt.show()


def pp_RefTESSol():
    #%% Daten einlesen
    inv = pd.read_csv('InvestSol.csv', sep=";")
    
    wnw = pd.read_csv('ErgebnisSol.csv', sep=";", index_col=0, parse_dates=True)
    
    
    #%% Ergebnisse der Investitionsrechnungen
    invest_TES = invest_stes(float(inv['Q_tes']))
    invest_ges = invest_TES + float(inv['invest_ges'])
    
    print("Referenzsystem + Wärmespeicher + Solarthermie")
    print("Erebnisse der Investitionsrechnungen:")
    print()
    
    netpresentvalue = npv(invest_ges, float(inv['objective']))/1e6
    print("Kapitalwert (NPV): " + '{:.3f}'.format(netpresentvalue) + " Mio. €")
    
    lcoh = LCOH(invest_ges, float(inv['ausgaben']), 
                float(inv['total_heat_demand']))
    print("Wärmegestehungskosten (LCOH): " + '{:.2f}'.format(lcoh) + " €/MWh")
    
    
    #%% Visualisierung
    ax = zplt.bar(data=wnw.sum(), ylabel='Gesamtwärmemenge in MWh')
    ax.grid(b=False, which='major', axis='x')
    
    ax = zplt.line(data=wnw, xlabel='Date', ylabel='Wärmeleistung in MW')
    ax.grid(b=False, which='minor', axis='x')
    
    ax = zplt.line(data=wnw[['BHKW', 'EHK', 'SLK', 'Wärmebedarf']], xlabel='Date', ylabel='Wärmeleistung in MW')
    ax.grid(b=False, which='minor', axis='x')
    
    ax = zplt.line(data=wnw[['TES Ein', 'TES Aus', 'Wärmebedarf']], xlabel='Date', ylabel='Wärmeleistung in MW')
    ax.grid(b=False, which='minor', axis='x')
    
    ax = zplt.line(data=wnw[['Solar', 'Wärmebedarf']], xlabel='Date', ylabel='Wärmeleistung in MW')
    ax.grid(b=False, which='minor', axis='x')
    
    shared.create_multipage_pdf(file_name='plotsSol.pdf')
    plt.show()
