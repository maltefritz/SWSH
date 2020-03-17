"""Functions for economical analysis and assesment.

Created on Thu Jan 16 10:13:55 2020

@author: Markus Brandt, Malte Fritz & Jonas Freißmann
"""

import numpy as np


# %% Kapitalwert
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


# %% Wärmegestehungskosten
def LCOH(invest, cashflow, Q, i=0.05, n=20):
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


# %% Investitionskosten
def invest_st(A, col_type=''):
    """Pehnt et al. 2017, Markus [38].

    A:                Kollektorfläche der Solarthermie
    col_type:         Kollektortyp der Solarthermie
    specific_coasts:  Spezifische Kosten
    invest:           Investitionskosten
    """
    if col_type == 'flat':
        specific_costs = -34.06 * np.log(A) + 592.48
        invest = A * specific_costs
        return invest
    elif col_type == 'vacuum':
        specific_costs = -40.63 * np.log(A) + 726.64
        invest = A * specific_costs
        return invest
    else:
        raise ValueError("Choose a valid collector type: 'flat' or 'vacuum'")


def invest_stes(Q, sponsorship=0.3):
    """Investment calculation for seasonal thermal energy storages.

    Q:              Kapazität des Speichers in MWh
    sponsorship:    rel. Förderung des Speichers (durch Bundesamt für
                    Wirtschaft und Ausfuhrkontrolle [10])
    q_V:            spez. volumetrische Energie
    """
    # V = Q / 0.3
    q_V = 0.07    # MWh/m³, unsere Annahme (siehe Whiteboardbild)
    V_stes = Q / q_V
    Q_specific_costs = 110    # In MA in €/m³ nach Pehnt et al. [38]
    stes_invest = V_stes * Q_specific_costs * (1 - sponsorship)
    return stes_invest
