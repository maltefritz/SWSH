# -*- coding: utf-8 -*-
"""
Created on Mon Jan  6 09:22:17 2020

@author: Malte Fritz
"""

from tespy.networks import network
from tespy.components import (sink, source, valve, turbine, splitter, merge,
                              condenser, pump, heat_exchanger_simple,
                              cycle_closer)
from tespy.connections import connection, bus, ref
from tespy.tools.characteristics import char_line

import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

# %% network

fluids = ['water']

nw = network(fluids=fluids, p_unit='bar', T_unit='C', h_unit='kJ / kg')

# %% components

# turbine part
turb_hp = turbine('high pressure turbine')
split = splitter('extraction splitter')
turb_lp= turbine('low pressure turbine')

# condenser and preheater
cond = condenser('condenser')
preheat = condenser('preheater')
mer = merge('waste steam merge')
val = valve('valve')

# feed water
pu = pump('pump')
sg = heat_exchanger_simple('steam generator')

closer = cycle_closer('cycle closer')

# source and sink for cooling water
dh_in = source('district heating backflow')
dh_out = sink('district heating feedflow')

# %% connections

# turbine part
cc_turb_hp = connection(closer, 'out1', turb_hp, 'in1')
turb_hp_split = connection(turb_hp, 'out1', split, 'in1')
split_preheat = connection(split, 'out1', preheat, 'in1')
split_turb_lp = connection(split, 'out2', turb_lp, 'in1')
nw.add_conns(cc_turb_hp, turb_hp_split, split_preheat, split_turb_lp)

# preheater and condenser
preheat_val = connection(preheat, 'out1', val, 'in1')
val_mer = connection(val, 'out1', mer, 'in2')
turb_lp_mer = connection(turb_lp, 'out1', mer, 'in1')
mer_cond = connection(mer, 'out1', cond, 'in1')
nw.add_conns(preheat_val, val_mer, turb_lp_mer, mer_cond)

# feed water
cond_pu = connection(cond, 'out1', pu, 'in1')
pu_preheat = connection(pu, 'out1', preheat, 'in2')
preheat_sg = connection(preheat, 'out2', sg, 'in1')
sg_cc = connection(sg, 'out1', closer, 'in1')
nw.add_conns(cond_pu, pu_preheat, preheat_sg, sg_cc)

# cooling water
dh_bf = connection(dh_in, 'out1', cond, 'in2')
dh_ff = connection(cond, 'out2', dh_out, 'in1')
nw.add_conns(dh_bf, dh_ff)

# %% busses

# motor efficiency
x = np.array([0, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55,
              0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 1, 1.05, 1.1, 1.15,
              1.2, 10])
y = 1 / (np.array([0.01, 0.3148, 0.5346, 0.6843, 0.7835, 0.8477, 0.8885,
                   0.9145, 0.9318, 0.9443, 0.9546, 0.9638, 0.9724, 0.9806,
                   0.9878, 0.9938, 0.9982, 1.0009, 1.002, 1.0015, 1, 0.9977,
                   0.9947, 0.9909, 0.9853, 0.9644])
         * 0.98)

mot1 = char_line(x=x, y=y)
mot2 = char_line(x=x, y=y)
mot3 = char_line(x=x, y=y)

# power bus
power_bus = bus('power')
power_bus.add_comps({'comp': turb_hp, 'char': mot1},
                    {'comp': turb_lp, 'char': mot2},
                    {'comp': pu, 'char': mot3})

# heating bus
heat_bus = bus('heat')
heat_bus.add_comps({'comp': cond})

nw.add_busses(power_bus, heat_bus)

# %% parametrization of components

turb_hp.set_attr(eta_s=0.9, design=['eta_s'],
                    offdesign=['eta_s_char', 'cone'])
turb_lp.set_attr(eta_s=0.9, design=['eta_s'],
                    offdesign=['eta_s_char', 'cone'])

cond.set_attr(pr1=0.99, pr2=0.99, ttd_u=12, design=['pr2', 'ttd_u'],
              offdesign=['zeta2', 'kA'])
preheat.set_attr(pr1=0.99, pr2=0.99, ttd_u=5,
                   design=['pr2', 'ttd_u', 'ttd_l'],
                   offdesign=['zeta2', 'kA'])

pu.set_attr(eta_s=0.8, design=['eta_s'], offdesign=['eta_s_char'])
sg.set_attr(pr=0.95)

# %% parametrization of connections

# fresh steam properties
cc_turb_hp.set_attr(p=100, T=550, fluid={'water': 1}, design=['p'])

# pressure extraction steam
turb_hp_split.set_attr(p=10, design=['p'])

# staring value for warm feed water
preheat_sg.set_attr(h0=310)

# cooling water inlet
dh_bf.set_attr(T=60, p=10, fluid={'water': 1})
dh_ff.set_attr(T=110)

# setting key parameters:
# Power of the plant
power_bus.set_attr(P=-5e6)


# %% solving

mode = 'design'

nw.solve(mode=mode)
nw.save('chp')
nw.print_results()

# path = 'chp'
# mode = 'offdesign'

# power_bus.set_attr(P=np.nan)
# m_design = cc_turb_hp.m.val_SI
# cc_turb_hp.set_attr(m=0.9*m_design)
# nw.solve(init_path=path, design_path=path, mode=mode)
# nw.print_results()

# # representation of part loads
# m_range = [1.05, 1, 0.9, 0.8, 0.7, 0.6]

# # temperatures for the heating system
# T_range = [120, 110, 100, 95, 90, 85, 80, 75, 70]

# df_P = pd.DataFrame(columns=m_range)
# df_Q = pd.DataFrame(columns=m_range)

# # iterate over temperatures
# for T in T_range:
#     dh_ff.set_attr(T=T)
#     Q = []
#     P = []
#     # iterate over mass flow
#     for m in m_range:
#         print('case: T='+str(T)+', load='+str(m))
#         cc_turb_hp.set_attr(m=m*m_design)

#         # use an initialisation file with parameters similar to next
#         # calculation
#         if T == T_range[0]:
#             nw.solve(init_path=path, design_path=path, mode=mode)
#         else:
#             nw.solve(init_path='chp_' + str(m), design_path=path, mode=mode)

#         nw.save('chp_' + str(m))
#         Q += [heat_bus.P.val]
#         P += [power_bus.P.val]

#     df_Q.loc[T] = Q
#     df_P.loc[T] = P

# df_P.to_csv('power.csv')
# df_Q.to_csv('heat.csv')
# # plotting
# df_P = pd.read_csv('power.csv', index_col=0)
# df_Q = pd.read_csv('heat.csv', index_col=0)

# colors = ['#00395b', '#74adc1', '#b54036', '#ec6707',
#           '#bfbfbf', '#999999', '#010101']

# fig, ax = plt.subplots()

# i = 0
# for T in T_range:
#     if T % 10 == 0:
#         plt.plot(df_Q.loc[T], df_P.loc[T], '-x', Color=colors[i],
#                   label='$T_{VL}$ = ' + str(T) + ' °C', markersize=7,
#                   linewidth=2)
#         i += 1

# ax.set_ylabel('$P$ in MW')
# ax.set_xlabel('$\dot{Q}$ in MW')
# plt.title('P-Q diagram for CHP with backpressure steam turbine')
# plt.legend(loc='lower left')
# ax.set_ylim([0, 7e6])
# ax.set_xlim([0, 14e6])
# plt.yticks(np.arange(0, 7e6, step=1e6), np.arange(0, 7, step=1))
# plt.xticks(np.arange(0, 14e6, step=2e6), np.arange(0, 14, step=2))

# plt.show()

# fig.savefig('PQ_diagram.svg')
