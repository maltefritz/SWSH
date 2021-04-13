# -*- coding: utf-8 -*-
"""Functions for calculation of economical and ecological parameters.

Created on Mon Feb  1 11:43:39 2021

@author: Jonas Freißmann
"""

import pandas as pd
from scipy.optimize import curve_fit
# import matplotlib.pyplot as plt


def npv(invest, cashflow, i=0.05, n=20):
    """Konstantin 2013, Markus [29].

    npv:        Kapitalwert (netpresentvalue)
    invest:     Investitionsausgaben zum Zeitpunkt t=0
    cashflow:   Differenz aller Einnahmen und Ausgaben (Zahlungsströme)
    i:          Kalkulationszinssatz
    n:          Betrachtungsdauer
    bwsf:       Barwert Summenfaktor
    """
    q = 1+i
    bwsf = (q**n - 1)/(q**n * (q - 1))

    npv = -invest + bwsf * cashflow
    return npv


def LCOH_old(invest, cashflow, Q, i=0.05, n=20):
    """Konstantin 2013, Markus [29].

    LCOH        Wärmegestehungskosten
    invest:     Investitionsausgaben zum Zeitpunkt t=0
    bwsf:       Barwert Summenfaktor
    cashflow:   Differenz aller Einnahmen und Ausgaben (Zahlungsströme)
                innerhalb des betrachteten Jahres
    Q:          Gesamte bereitgestellte Wärmemenge pro Jahr
    i:          Kalkulationszinssatz
    n:          Betrachtungsdauer
    """
    q = 1 + i
    bwsf = (q**n - 1)/(q**n * (q - 1))

    LCOH = abs(-invest * bwsf**(-1) + cashflow) / Q
    return LCOH


def LCOH(invest, cost, Q, revenue=0, i=0.05, n=20):
    """Konstantin 2013, Markus [29].

    LCOH        Wärmegestehungskosten
    invest:     Investitionsausgaben zum Zeitpunkt t=0
    bwsf:       Barwert Summenfaktor
    cashflow:   Differenz aller Einnahmen und Ausgaben (Zahlungsströme)
                innerhalb des betrachteten Jahres
    Q:          Gesamte bereitgestellte Wärmemenge pro Jahr
    i:          Kalkulationszinssatz
    n:          Betrachtungsdauer
    """
    q = 1 + i
    bwsf = (q**n - 1)/(q**n * (q - 1))

    LCOH = (invest + bwsf * (cost - revenue))/(bwsf * Q)
    return LCOH


def emission_calc(data_emission):
    """Calculate the emissions compared with overall and displacement mix."""
    co2 = pd.read_csv('input\\emissions2016.csv', sep=";")
    co2['Date'] = pd.to_datetime(co2['Date'], format='%d.%m.%Y %H:%M')
    co2.set_index('Date', inplace=True)

    Em_om = list()
    Em_dm = list()

    e_fuel = 0.2012    # in t/MWh aus "Emissionsbewertung Daten"

    for idx_em, idx_co2 in zip(data_emission.index, co2.index):
        Em_om.append(
            data_emission.loc[idx_em, 'H_source'] * e_fuel
            + data_emission.loc[idx_em, 'P_source'] * co2.loc[idx_co2, 'EF om']
            - (data_emission.loc[idx_em, 'P_spot_market']
               * co2.loc[idx_co2, 'EF om'])
            )

        Em_dm.append(
            data_emission.loc[idx_em, 'H_source'] * e_fuel
            + data_emission.loc[idx_em, 'P_source'] * co2.loc[idx_co2, 'EF dm']
            - (data_emission.loc[idx_em, 'P_spot_market']
               * co2.loc[idx_co2, 'EF dm'])
            )

    dfEm = pd.DataFrame({'date': data_emission.index,
                         'overall mix': Em_om,
                         'displacement mix': Em_dm})
    dfEm.set_index('date', inplace=True)

    return dfEm


def invest_stes(Q, sponsorship=0.3):
    """Investment calculation for seasonal thermal energy storages.

    Q:              Kapazität des Speichers in MWh
    sponsorship:    rel. Förderung des Speichers (durch Bundesamt für
                    Wirtschaft und Ausfuhrkontrolle [10])
    q_V:            spez. volumetrische Energie
    """
    # Kostendegression STES
    def potential_func(x, a, b):
        return a * x ** b

    if Q == 0:
        return 0

    x = [500, 5000, 62000]
    y = [320, 110, 2359594/62000]

    params, params_covariance = curve_fit(potential_func, x, y)

    # V = Q / 0.3
    q_V = 0.07    # MWh/m³, unsere Annahme (siehe Whiteboardbild)
    V_stes = Q / q_V
    Q_specific_costs = params[0] * V_stes ** params[1]
    stes_invest = V_stes * Q_specific_costs * (1 - sponsorship)

    return stes_invest


def chp_bonus(P, use_case):
    """Calculate chp bonus based on nominal power output.

    P:           nomimal power output of chp unit (int or float)
    use_case:    either 'grid' or 'self-sufficient' (str)
    bonus:       calculated chp bonus in ct/kWh (float)
    """
    if P == 0:
        return 0
    if use_case == 'grid':
        bonus_intervals = [8.0, 6.0, 5.0, 4.4, 3.4]
    elif use_case == 'self-sufficient':
        bonus_intervals = [4.0, 3.0, 2.0, 1.5, 1.0]
    else:
        print('No valid use case given.')

    # Defined intervals for power output (KWKG)
    P_intervals = [0.0, 50.0, 100.0, 250.0, 2000.0]

    # Calculate steps between power output intervals
    P_steps = list()
    for i in range(1, len(P_intervals)):
        P_steps += [P_intervals[i] - P_intervals[i-1]]

    # Check at which index the last power value is bigger than P
    idx = len(P_intervals) - 1
    for i in range(len(P_intervals)):
        if P < P_intervals[i]:
            idx = i - 1
            break

    # Add the weighted bonus values for all complete intervals
    bonus_weighted = 0
    for i in range(idx):
        bonus_weighted += P_steps[i] * bonus_intervals[i]

    # Add the weighted bonus for the last incomplete interval
    bonus_weighted += (P - P_intervals[idx]) * bonus_intervals[idx]

    # Calculate the nominal bonus by deviding by the sum of weights (P)
    bonus = bonus_weighted / P

    return bonus


# if __name__ == '__main__':
#     x = [*range(10, 5010, 10)]
#     y = [chp_bonus(x_i, 'grid') for x_i in x]

#     fig, ax = plt.subplots()

#     ax.plot(x, y)
#     ax.grid()

#     plt.show()
