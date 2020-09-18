# -*- coding: utf-8 -*-
"""
Created on Tue Sep  8 13:07:53 2020

@author: Jonas Freißmann
"""

import json
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl
# from matplotlib.animation import ArtistAnimation

from solphPQ import main
from znes_plotting.shared import create_multipage_pdf

plt.rcParams['pdf.fonttype'] = 42
mpl.rcParams['savefig.bbox'] = 'tight'
mpl.rcParams['savefig.pad_inches'] = 0.1
mpl.rcParams['font.family'] = 'Carlito'
mpl.rcParams['font.size'] = 20

colors = ['#00395b', '#b54036', '#74adc0', '#ec6707', '#bfbfbf', '#999999',
          '#010101', '#00395b', '#74adc1', '#b54036', '#ec6707', '#10b4e6']

with open('ccet_QPdata.json', 'r') as file:
    QP_data = json.load(file)

solphparams = pd.read_csv('solphparams.csv', sep=';', index_col=0)

# fig, ax = plt.subplots(figsize=[7.5, 5])

# ax.plot([Q/1e6 for Q in QP_data['65']['Q']],
#         [P/1e6 for P in QP_data['65']['P']],
#         'o-', MarkerSize=4, label='65 °C', color=colors[0])

# ax.plot([Q/1e6 for Q in QP_data['91']['Q']],
#         [P/1e6 for P in QP_data['91']['P']],
#         'o-', MarkerSize=4, label='91 °C', color=colors[3])

# ax.plot([Q/1e6 for Q in QP_data['123']['Q']],
#         [P/1e6 for P in QP_data['123']['P']],
#         'o-', MarkerSize=4, label='123 °C', color=colors[1])

# ax.legend(loc='lower center', bbox_to_anchor=[0.5, -0.36], ncol=3)
# ax.set_xlabel('Wärmestrom Qdot in MW')
# ax.set_ylabel('El. Leistung P in MW')
# ax.grid(linestyle='-', color='k')
# ax.grid(b=True, which='minor', linestyle='--')
# ax.yaxis.set_major_locator(mpl.ticker.MultipleLocator(25))
# ax.yaxis.set_minor_locator(mpl.ticker.MultipleLocator(5))
# ax.xaxis.set_minor_locator(mpl.ticker.MultipleLocator(5))
# fig.suptitle(('TESPy Simulationsergebnisse bei \nverschiedenen '
#               + 'Vorlauftemperaturen'),
#               y=1.04)

# tot_time = 0
# for row in QP_data.keys():
#     plt.scatter(row, QP_data[row]['Laufzeit'])
#     tot_time += QP_data[row]['Laufzeit']

# print(round(tot_time/60, 1))

temprange = [121, 122, 123, 124]
# temprange = [*range(65, 125, 2)]
# temprange = [*range(65, 125)]
unsolvableVals = [74, 75, 76, 79]

for val in unsolvableVals:
    if val in temprange:
        temprange.remove(val)
# axs = list()

for temp in temprange:
    params = solphparams.loc[temp].copy()

    params['P_max_woDH'] /= 1e6
    params['P_min_woDH'] /= 1e6
    params['Q_CW_min'] /= 1e6
    params['Q_in'] /= 1e6
    # params['eta_el_max'] = 0.525
    # params['eta_el_min'] = 0.42
    # params['P_max_woDH'] = 145
    # params['Q_in'] = 295
    # params['Q_CW_min'] = -6.78
    # params['H_L_FG_share_max'] = 0.237

    (data_wnw, data_kwk) = main(params)

    fig, ax = plt.subplots(figsize=[7, 5])

    ax.scatter(data_kwk.iloc[:, -1], data_kwk.iloc[:, 1],
               label='solph', color=colors[0])
    ax.scatter([Q/1e6 for Q in QP_data[str(temp)]['Q']],
               [P/1e6 for P in QP_data[str(temp)]['P']],
               label='TESPy', color=colors[3])

    ax.legend(loc='lower right')
    ax.set_xlabel('Wärmestrom Qdot in MW')
    ax.set_ylabel('El. Leistung P in MW')
    ax.grid(linestyle='--')
    ax.set_xlim(left=0, right=100)
    ax.set_ylim(bottom=0, top=175)
    ax.yaxis.set_major_locator(mpl.ticker.MultipleLocator(25))
    ax.yaxis.set_minor_locator(mpl.ticker.MultipleLocator(5))
    ax.xaxis.set_minor_locator(mpl.ticker.MultipleLocator(5))
    fig.suptitle('Betriebsfeld der GuD-Anlage bei ' + str(temp) + ' °C')
    # axs.append([ax])

    # plt.savefig('ccet_approx_' + str(temp) + '.pdf')

# anim = ArtistAnimation(fig, axs, blit=True)

# anim.save('ccet_animation.gif', writer='imagemagick')

# fig, axs = plt.subplots(3, 1, figsize=[8, 10], sharex=True)

# axs[0].plot(solphparams.index, solphparams.loc[:, 'P_max_woDH']/1e6,
#             label='P_max_woDH', color=colors[0])
# axs[1].plot(solphparams.index, solphparams.loc[:, 'P_min_woDH']/1e6,
#             label='P_min_woDH', color=colors[1])
# axs[2].plot(solphparams.index, solphparams.loc[:, 'Q_CW_min']/1e6,
#             label='Q_CW_min', color=colors[2])
# axs[2].set_xlabel('Vorlauftemperatur in °C')
# fig.suptitle('Verlauf verschiedener Parameter\n(alle Werte in MW)', y=0.96)

# for ax in axs:
#     ax.grid(linestyle='--')
#     ax.legend()

# fig, axs = plt.subplots(4, 1, figsize=[8, 10], sharex=True)

# axs[0].plot(solphparams.index, solphparams.loc[:, 'eta_el_max'],
#             label='eta_el_max', color=colors[0])
# axs[1].plot(solphparams.index, solphparams.loc[:, 'eta_el_min'],
#             label='eta_el_min', color=colors[1])
# axs[2].plot(solphparams.index, solphparams.loc[:, 'H_L_FG_share_max'],
#             label='H_L_FG_share_max', color=colors[2])
# axs[3].plot(solphparams.index, solphparams.loc[:, 'beta'],
#             label='beta', color=colors[3])
# axs[3].set_xlabel('Vorlauftemperatur in °C')
# fig.suptitle('Verlauf verschiedener Parameter', y=0.94)

# for ax in axs:
#     ax.grid(linestyle='--')
#     ax.legend()

# create_multipage_pdf('ccet_Tvar_approx_plots_fullrange.pdf')

plt.show()

# Parameter bei 65 °C

# params['P_max_woDH'] /= 1e6
# params['P_min_woDH'] /= 1e6
# params['Q_CW_min'] /= 1e6
# params['Q_in'] /= 1e6
# params['eta_el_max'] = 0.552
# params['eta_el_min'] = 0.443
# params['P_max_woDH'] = 157
# params['Q_in'] = 280
# params['Q_CW_min'] = 14
# params['H_L_FG_share_max'] = 0.168

# Parameter bei 91 °C

# params['P_max_woDH'] /= 1e6
# params['P_min_woDH'] /= 1e6
# params['Q_CW_min'] /= 1e6
# params['Q_in'] /= 1e6
# params['eta_el_max'] = 0.546
# params['eta_el_min'] = 0.434
# params['P_max_woDH'] = 152.5
# params['Q_in'] = 275
# params['Q_CW_min'] = 15
# params['H_L_FG_share_max'] = 0.168

# Parameter bei 123 °C

# params['P_max_woDH'] /= 1e6
# params['P_min_woDH'] /= 1e6
# params['Q_CW_min'] /= 1e6
# params['Q_in'] /= 1e6
# params['eta_el_max'] = 0.525
# params['eta_el_min'] = 0.42
# params['P_max_woDH'] = 145
# params['Q_in'] = 295
# params['Q_CW_min'] = 17.3
# params['H_L_FG_share_max'] = 0.18
