"""TESPy model of a combined cycle with extraction turbine for distric heating.

Created on Thu Jul 12 07:45:32 2018

@author: Malte Fritz & Jonas Freißmann
"""

from tespy.components import (Sink, Source, Splitter, Merge, Drum, Turbine,
                              Compressor, Pump, Condenser, HeatExchanger,
                              CombustionChamber, Valve)
from tespy.connections import Bus, Ref, Connection
from tespy.networks import Network
from tespy.tools.characteristics import CharLine
from tespy.tools import document_model

from os.path import abspath, join
import json
from time import time
from tespy.tools.characteristics import load_default_char as ldc
import numpy as np
from sklearn.linear_model import LinearRegression
from matplotlib import pyplot as plt
import matplotlib as mpl
import pandas as pd

plt.rcParams['pdf.fonttype'] = 42
mpl.rcParams['savefig.bbox'] = 'tight'
mpl.rcParams['savefig.pad_inches'] = 0.1
mpl.rcParams['font.family'] = 'Carlito'
mpl.rcParams['font.size'] = 20
mpl.rcParams['figure.max_open_warning'] = 50

Q_N = abs(float(input('Gib die Nennwaermeleistung in MW ein: ')))*-1e6

# %% network
fluid_list = ['Ar', 'N2', 'O2', 'CO2', 'CH4', 'H2O']

nw = Network(fluids=fluid_list, p_unit='bar', T_unit='C', h_unit='kJ / kg',
             p_range=[1, 100], T_range=[10, 1500], h_range=[10, 4000])

# %% components
# gas turbine part
comp = Compressor('compressor')
comp_fuel = Compressor('fuel compressor')
c_c = CombustionChamber('combustion')
g_turb = Turbine('gas turbine')

CH4 = Source('fuel source')
air = Source('ambient air')

# waste heat recovery
suph = HeatExchanger('superheater')
evap = HeatExchanger('evaporator')
drum = Drum('drum')
eco = HeatExchanger('economizer')
ch = Sink('chimney')

# steam turbine part
turb_hp = Turbine('steam turbine high pressure')
cond_dh = Condenser('district heating condenser')
mp_split = Splitter('mp split')
turb_lp = Turbine('steam turbine low pressure')
cond = Condenser('condenser')
merge = Merge('merge')
pump1 = Pump('feed water pump 1')
pump2 = Pump('feed water pump 2')
ls_out = Sink('ls sink')
ls_in = Source('ls source')
mp_valve = Valve('mp valve')

# district heating
dh_in = Source('district heating backflow')
dh_out = Sink('district heating feedflow')

# cooling water
cw_in = Source('cooling water backflow')
cw_out = Sink('cooling water feedflow')

# %% connections
# gas turbine part
c_in = Connection(air, 'out1', comp, 'in1')
c_out = Connection(comp, 'out1', c_c, 'in1')
fuel_comp = Connection(CH4, 'out1', comp_fuel, 'in1')
comp_cc = Connection(comp_fuel, 'out1', c_c, 'in2')
gt_in = Connection(c_c, 'out1', g_turb, 'in1')
gt_out = Connection(g_turb, 'out1', suph, 'in1')

nw.add_conns(c_in, c_out, fuel_comp, comp_cc, gt_in, gt_out)

# waste heat recovery (flue gas side)
suph_evap = Connection(suph, 'out1', evap, 'in1')
evap_eco = Connection(evap, 'out1', eco, 'in1')
eco_ch = Connection(eco, 'out1', ch, 'in1')

nw.add_conns(suph_evap, evap_eco, eco_ch)

# waste heat recovery (water side)
eco_drum = Connection(eco, 'out2', drum, 'in1')
drum_evap = Connection(drum, 'out1', evap, 'in2')
evap_drum = Connection(evap, 'out2', drum, 'in2')
drum_suph = Connection(drum, 'out2', suph, 'in2')

nw.add_conns(eco_drum, drum_evap, evap_drum, drum_suph)

# steam turbine
suph_ls = Connection(suph, 'out2', ls_out, 'in1')
ls = Connection(ls_in, 'out1', turb_hp, 'in1')
mp = Connection(turb_hp, 'out1', mp_split, 'in1')

# extraction
mp_ws = Connection(mp_split, 'out1', cond_dh, 'in1')
mp_c = Connection(cond_dh, 'out1', pump1, 'in1')
mp_fw = Connection(pump1, 'out1', merge, 'in1')

nw.add_conns(suph_ls, ls, mp, mp_ws, mp_c, mp_fw)

# backpressure
mp_v = Connection(mp_split, 'out2', mp_valve, 'in1')
mp_ls = Connection(mp_valve, 'out1', turb_lp, 'in1')
lp_ws = Connection(turb_lp, 'out1', cond, 'in1')
lp_c = Connection(cond, 'out1', pump2, 'in1')
lp_fw = Connection(pump2, 'out1', merge, 'in2')
fw = Connection(merge, 'out1', eco, 'in2')

nw.add_conns(mp_v, mp_ls, lp_ws, lp_c, lp_fw, fw)

# district heating
dh_i = Connection(dh_in, 'out1', cond_dh, 'in2')
dh_o = Connection(cond_dh, 'out2', dh_out, 'in1')

# cooling water
cw_i = Connection(cw_in, 'out1', cond, 'in2')
cw_o = Connection(cond, 'out2', cw_out, 'in1')

nw.add_conns(cw_i, cw_o, dh_i, dh_o)

# %% busses

# motor efficiency
x = np.array([0, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55,
              0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 1, 1.05, 1.1, 1.15,
              1.2, 10])
y = 1 / (np.array([0.01, 0.3148, 0.5346, 0.6843, 0.7835, 0.8477, 0.8885,
                   0.9145, 0.9318, 0.9443, 0.9546, 0.9638, 0.9724, 0.9806,
                   0.9878, 0.9938, 0.9982, 1.0009, 1.002, 1.0015, 1, 0.9977,
                   0.9947, 0.9909, 0.9853, 0.9644])
         * 0.97)

mot1 = CharLine(x=x, y=y)
mot2 = CharLine(x=x, y=y)
mot3 = CharLine(x=x, y=y)

# generator efficiency
x = np.array([0.100, 0.345, 0.359, 0.383, 0.410, 0.432, 0.451, 0.504, 0.541,
              0.600, 0.684, 0.805, 1.000, 1.700, 10])
y = np.array([0.976, 0.989, 0.990, 0.991, 0.992, 0.993, 0.994, 0.995, 0.996,
              0.997, 0.998, 0.999, 1.000, 0.999, 0.99]) * 0.984

gen1 = CharLine(x=x, y=y)
gen2 = CharLine(x=x, y=y)
gen3 = CharLine(x=x, y=y)

power = Bus('power output')
power.add_comps({'c': g_turb, 'char': gen1}, {'c': comp, 'char': 1},
                {'c': comp_fuel, 'char': mot1}, {'c': turb_hp, 'char': gen2},
                {'c': pump1, 'char': mot2},
                {'c': turb_lp, 'char': gen3}, {'c': pump2, 'char': mot3})

gt_power = Bus('gas turbine power output')
gt_power.add_comps({'c': g_turb}, {'c': comp})

heat_out = Bus('heat output')
heat_out.add_comps({'c': cond_dh})

heat_cond = Bus('heat cond')
heat_cond.add_comps({'c': cond})

heat_in = Bus('heat input')
heat_in.add_comps({'c': c_c})

nw.add_busses(power, gt_power, heat_out, heat_cond, heat_in)

# %% component parameters

# characteristic line for compressor isentropic efficiency
x = np.array([0.000, 0.400, 1.000, 1.600, 2.000])
y = np.array([0.500, 0.900, 1.000, 1.050, 0.9500])
cp_char1 = dict(char_func=CharLine(x, y), param='m')
cp_char2 = dict(char_func=CharLine(x, y), param='m')

# characteristic line for turbine isentropic efficiency
x = np.array([0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1,
              1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 2.0, 2.1, 2.2, 2.3,
              2.4, 2.5])
y = np.array([0.7, 0.7667, 0.8229, 0.8698, 0.9081, 0.9387, 0.9623, 0.9796,
              0.9913, 0.9979, 1.0, 0.9981, 0.9926, 0.9839, 0.9725, 0.9586,
              0.9426, 0.9248, 0.9055, 0.8848, 0.8631, 0.8405, 0.8171, 0.7932,
              0.7689, 0.7444])
eta_s_gt = dict(char_func=CharLine(x, y), param='m')

# characteristic line for pump isentropic efficiency
x = np.array([0, 0.0625, 0.125, 0.1875, 0.25, 0.3125, 0.375, 0.4375, 0.5,
              0.5625, 0.6375, 0.7125, 0.7875, 0.9, 0.9875, 1, 1.0625, 1.125,
              1.175, 1.2125, 1.2375, 1.25, 1.5])
y = np.array([0.008, 0.139, 0.273, 0.400, 0.519, 0.626, 0.722, 0.806, 0.875,
              0.931, 0.973, 1.001, 1.020, 1.016, 1.005, 1.000, 0.975, 0.929,
              0.883, 0.838, 0.784, 0.761, 0.2])
eta_s_p1 = dict(char_func=CharLine(x, y), param='m')
eta_s_p2 = dict(char_func=CharLine(x, y), param='m')

# characteristic line for district heating condenser kA hot side
x = np.array([0, 0.0001, 0.001, 0.01, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8,
              0.9, 1.0, 2.0])
y = np.array([0.025, 0.05, 0.1, 0.2, 0.4, 0.85, 0.89, 0.92, 0.945,
              0.965, 0.98, 0.99, 0.995, 1.000, 1.05])
cd_char_hot = dict(char_func=CharLine(x, y), param='m')

# gas turbine
comp.set_attr(pr=15, eta_s=0.85, eta_s_char=cp_char1, design=['pr', 'eta_s'],
              offdesign=['eta_s_char'])
comp_fuel.set_attr(eta_s=0.85, eta_s_char=cp_char2, design=['eta_s'],
                   offdesign=['eta_s_char'])
g_turb.set_attr(eta_s=0.9, eta_s_char=eta_s_gt, design=['eta_s'],
                offdesign=['eta_s_char', 'cone'])
c_c.set_attr(lamb=2.5)

eta_s_char1 = ldc('turbine', 'eta_s_char', 'TRAUPEL', CharLine)
eta_s_char2 = ldc('turbine', 'eta_s_char', 'TRAUPEL', CharLine)

# steam turbine
suph.set_attr(pr1=0.99, pr2=0.98, ttd_u=50, design=['pr1', 'pr2', 'ttd_u'],
              offdesign=['zeta1', 'zeta2', 'kA_char'])
eco.set_attr(pr1=0.99, pr2=1, design=['pr1', 'pr2'],
             offdesign=['zeta1', 'zeta2', 'kA_char'])
evap.set_attr(pr1=0.99, ttd_l=20, design=['pr1', 'ttd_l'],
              offdesign=['zeta1', 'kA_char'])
turb_hp.set_attr(eta_s=0.88, eta_s_char=eta_s_char1, design=['eta_s'],
                 offdesign=['eta_s_char', 'cone'])
turb_lp.set_attr(eta_s=0.88, eta_s_char=eta_s_char2, design=['eta_s'],
                 offdesign=['eta_s_char', 'cone'])

cond_dh.set_attr(kA_char1=cd_char_hot, pr1=0.99, pr2=0.98, ttd_u=5,
                 design=['ttd_u', 'pr2'], offdesign=['zeta2', 'kA_char'])
cond.set_attr(pr1=0.99, pr2=0.98, ttd_u=5, design=['ttd_u', 'pr2'],
              offdesign=['zeta2', 'kA_char'])

pump1.set_attr(eta_s=0.8, eta_s_char=eta_s_p1, design=['eta_s'],
               offdesign=['eta_s_char'])
pump2.set_attr(eta_s=0.8, eta_s_char=eta_s_p2, design=['eta_s'],
               offdesign=['eta_s_char'])

mp_valve.set_attr(pr=1, design=['pr'])

# %% connection parameters

# gas turbine
c_in.set_attr(T=20, p=1, fluid={'Ar': 0.0129, 'N2': 0.7553, 'H2O': 0,
                                'CH4': 0, 'CO2': 0.0004, 'O2': 0.2314})
# gt_in.set_attr(T=1315)
# gt_out.set_attr(p=1.05)
fuel_comp.set_attr(p=Ref(c_in, 1, 0), T=Ref(c_in, 1, 0), h0=800,
                   fluid={'CO2': 0.04, 'Ar': 0, 'N2': 0,
                          'O2': 0, 'H2O': 0, 'CH4': 0.96})

# waste heat recovery
eco_ch.set_attr(T=142, design=['T'], p=1.02)

# steam turbine
evap_drum.set_attr(m=Ref(drum_suph, 4, 0))
suph_ls.set_attr(p=130, fluid={'CO2': 0, 'Ar': 0, 'N2': 0,
                               'O2': 0, 'H2O': 1, 'CH4': 0},
                 design=['p'])
ls.set_attr(p=Ref(suph_ls, 1, 0), h=Ref(suph_ls, 1, 0))

# mp.set_attr(p=5, design=['p'])
mp_ls.set_attr(m=Ref(mp, 0.2, 0))
# lp_ws.set_attr(p=0.8, design=['p'])

# district heating - dh_i.set_attr(T=60) läuft es
dh_i.set_attr(T=50, p=10, fluid={'CO2': 0, 'Ar': 0, 'N2': 0,
                                 'O2': 0, 'H2O': 1, 'CH4': 0})
dh_o.set_attr(T=90)

# cooling water
cw_i.set_attr(T=15, p=5, fluid={'CO2': 0, 'Ar': 0, 'N2': 0,
                                'O2': 0, 'H2O': 1, 'CH4': 0})

cw_o.set_attr(T=30, design=['T'], offdesign=['m'])

# %% design case 1:
# district heating condeser layout


# Q_N=65

heat_out.set_attr(P=Q_N)
nw.solve(mode='design', init_path='cet_stable')
nw.print_results()
nw.save('cet_design_maxQ')
gt_power_design = gt_power.P.val
print(heat_out.P.val / heat_in.P.val, power.P.val / heat_in.P.val)
print(heat_out.P.val, power.P.val, heat_in.P.val)
print(gt_power.P.val)

# %% design case 2:
# maximum gas turbine minimum heat extraction (cet_design_minQ)
gt_power.set_attr(P=gt_power_design)
heat_out.set_attr(P=-10e6)

# local offdesign for district heating condenser
cond_dh.set_attr(local_offdesign=True, design_path='cet_design_maxQ')
pump1.set_attr(local_offdesign=True, design_path='cet_design_maxQ')
mp_ws.set_attr(local_offdesign=True, design_path='cet_design_maxQ')
mp_c.set_attr(local_offdesign=True, design_path='cet_design_maxQ')
mp_fw.set_attr(local_offdesign=True, design_path='cet_design_maxQ')
dh_i.set_attr(local_offdesign=True, design_path='cet_design_maxQ')
dh_o.set_attr(local_offdesign=True, design_path='cet_design_maxQ')

mp_ls.set_attr(m=np.nan)
nw.solve(mode='design', design_path='cet_design_maxQ')
nw.save('cet_design_minQ')
nw.print_results()
m_lp_max = mp_ls.m.val_SI
print(heat_out.P.val / heat_in.P.val, power.P.val / heat_in.P.val)
print(heat_out.P.val, power.P.val)
print(mp_ls.m.val_SI / m_lp_max)

# %% offdesign

    # %% merge the plants together: offdesign test

print('no heat, full power')
# nw.set_printoptions(print_level='none')

nw.solve(mode='offdesign', design_path='cet_design_minQ')
nw.print_results()
# P += [abs(power.P.val)]
# Q += [abs(heat_out.P.val)]
# Q_cond += [abs(heat_cond.P.val)]
# Q_ti += [heat_in.P.val]

# Q_in = Q_ti[-1]

solphparams = pd.DataFrame(columns=['P_max_woDH', 'eta_el_max',
                                    'P_min_woDH', 'eta_el_min',
                                    'H_L_FG_share_max',
                                    'Q_CW_min',
                                    'beta'])

QPjson = dict()

cmap_list = []
# ausnahmeWert = 74.4
# T_range = [*range(65, 74), ausnahmeWert, *range(75, 125)]
# T_range = [*range(65, 125)]
# T_range = [*range(65, 125, 2)]
# T_range = [121, 122, 123, 124]
T_range = [95, 96, 97, 98]
unsolvableVals = [74, 75, 76, 79]

for val in unsolvableVals:
    if val in T_range:
        T_range.remove(val)

for Tval in T_range:
    start_time = time()
    P = []
    Q = []
    Q_cond = []
    Q_ti = []

    print('#######', Tval, '#######')
    dh_o.set_attr(T=int(Tval))
        # %%move to maximum heat extraction at maximum gas turbine power
    gt_power.set_attr(P=gt_power_design)
    heat_out.set_attr(P=-10e6)

    Q_step = np.linspace(-10e6, Q_N, num=7)

    for Q_val in Q_step:
        heat_out.set_attr(P=Q_val)
        nw.solve(mode='offdesign', design_path='cet_design_minQ')
        print(Q_val)
        P += [abs(power.P.val)]
        Q += [abs(heat_out.P.val)]
        Q_cond += [abs(heat_cond.P.val)]
        Q_ti += [heat_in.P.val]

        # %% from minimum to maximum gas turbine power at maximum heat extraction

    print('#######', Tval, '#######')
    print('maximum power to minimum power at maximum heat')

    heat_out.set_attr(P=np.nan)
    # mp_ls.set_attr(m=mp_ls.m.val)
    lp_ws.set_attr(m=lp_ws.m.val)
    nw.solve(mode='offdesign', design_path='cet_design_minQ')

    # parameter for top_right:
    P_t_r = P[-1]
    Q_t_r = Q[-1]
    Q_cond_t_r = Q_cond[-1]
    Q_in_t_r = Q_ti[-1]

    TL_step = np.linspace(0.9, 0.3, num=7)

    for TL_val in TL_step:
        gt_power.set_attr(P=gt_power_design * TL_val)
        nw.solve(mode='offdesign', design_path='cet_design_minQ')
        P += [abs(power.P.val)]
        Q += [abs(heat_out.P.val)]
        Q_cond += [abs(heat_cond.P.val)]
        Q_ti += [heat_in.P.val]
        print('Frischdampfmassenstrom: ', '{:.1f}'.format(ls.m.val))
        print('MD-Dampfmassenstrom: ', '{:.1f}'.format(mp_ls.m.val))
        print('ND-Dampfmassenstrom: ', '{:.1f}'.format(lp_ws.m.val))
        print('GT-Massenstrom: ', '{:.1f}'.format(gt_in.m.val))
    Q_TL = heat_out.P.val

    # parameter for buttom_right:
    P_b_r = P[-1]
    Q_b_r = Q[-1]
    Q_cond_b_r = Q_cond[-1]
    Q_in_b_r = Q_ti[-1]

        # %% back to design case, but minimum gas turbine power

    print('#######', Tval, '#######')
    print('maximum heat to minimum heat, minimum power')

    lp_ws.set_attr(m=np.nan)

    Q_step = np.linspace(Q_TL, -1e5, num=9, endpoint=False)

    for Q_val in Q_step:
        heat_out.set_attr(P=Q_val)
        nw.solve(mode='offdesign', design_path='cet_design_minQ')
        print(Q_val)
        P += [abs(power.P.val)]
        Q += [abs(heat_out.P.val)]
        Q_cond += [abs(heat_cond.P.val)]
        Q_ti += [heat_in.P.val]

    # %% postprocessing

    # P_Q_Diagramm
    # cmap_list += [Tval]*23
    # fig, ax = plt.subplots(figsize=[11, 7])

    # scatterplot = ax.scatter([Qval/1e6 for Qval in Q],
    #                          [Pval/1e6 for Pval in P],
    #                          c=cmap_list, cmap='inferno', alpha=0.7,
    #                          s=80, edgecolor='k', linewidth=0.25)

    # cbar = plt.colorbar(scatterplot, ax=ax)
    # cbar.set_label('Vorlauftemperatur in °C')
    # ax.grid(linestyle='--')
    # ax.set_xlabel('Wärmestrom Qdot in MW')
    # ax.set_ylabel('El. Leistung P in MW')
    # # ax.set_title('Vorlauftemperatur = ' + str(Tval) + ' °C')
    # plt.show()
    end_time = time()
    elapsed_time = end_time - start_time

    QPjson[Tval] = {'Q': Q, 'P': P,
                    'Laufzeit': elapsed_time}

    # lineare Regression
    x = np.array(Q[4:7]).reshape((-1, 1))
    y = np.array(P[4:7])

    linreg = LinearRegression().fit(x, y)
    P_t_l = linreg.intercept_

    x = np.array(Q[14:]).reshape((-1, 1))
    y = np.array(P[14:])

    linreg = LinearRegression().fit(x, y)
    P_b_l = linreg.intercept_

    # Mittelwerte der zugeführten Wärme
    Q_in_t = sum(Q_ti[4:7])/len(Q_ti[4:7])
    Q_in_b = sum(Q_ti[14:])/len(Q_ti[14:])

    # Q_in top and bottom
    x = np.array(Q[4:7]).reshape((-1, 1))
    y = np.array(Q_ti[4:7])

    linreg = LinearRegression().fit(x, y)
    Q_in_t_l_linreg = linreg.intercept_

    x = np.array(Q[14:]).reshape((-1, 1))
    y = np.array(Q_ti[14:])

    linreg = LinearRegression().fit(x, y)
    Q_in_b_l_linreg = linreg.intercept_

    # solph Parameter

    ratio = (Q_b_r - Q_t_r + P_b_r - P_t_r)/(Q_in_b_r - Q_in_t_r)
    H_L = 1 - ratio
    Q_CW = Q_in_t_r * ratio - P_t_r - Q_t_r
    print('{:.3f}'.format(H_L), '{:.1f}'.format(Q_CW/1e6),
          '{:.3f}'.format(ratio))

    solphparams.loc[Tval, 'Q_in'] = Q_in_t_l_linreg
    solphparams.loc[Tval, 'P_max_woDH'] = P_t_l
    solphparams.loc[Tval, 'eta_el_max'] = P_t_l/Q_in_t_l_linreg
    solphparams.loc[Tval, 'P_min_woDH'] = P_b_l
    solphparams.loc[Tval, 'eta_el_min'] = P_b_l/Q_in_b_l_linreg
    beta_unten = abs((P_b_r - P_b_l) / Q_b_r)
    beta_oben = abs((P_t_r - P_t_l) / Q_t_r)
    solphparams.loc[Tval, 'beta'] = (beta_oben + beta_unten) / 2

    # not_used_high = Q_in_t - P_t_l - Q_t_r * (1-solphparams.loc[Tval, 'beta'])
    # not_used_low = Q_in_b - P_b_l - Q_b_r * (1-solphparams.loc[Tval, 'beta'])

    # not_used_high = Q_in_t - P_t_r - Q_t_r
    # not_used_low = Q_in_b - P_b_r - Q_b_r

    # H_L = (not_used_high - not_used_low)/(Q_in_t - Q_in_b)
    # Q_CW = not_used_low - H_L * Q_in_b

    # not_used_high = Q_in_t_r - P_t_r - Q_t_r
    # not_used_low = Q_in_b_r - P_b_r - Q_b_r

    # H_L = (not_used_high - not_used_low)/(Q_in_t_r - Q_in_b_r)
    # Q_CW = not_used_low - H_L * Q_in_b_r

    # H_L_FG_t_r = 1-(P_t_r + Q_t_r + Q_cond_t_r) / Q_in_t_r
    # H_L_FG_b_r = 1-(P_b_r + Q_b_r + Q_cond_b_r) / Q_in_b_r
    # solphparams.loc[Tval, 'H_L_FG_share_max'] = (H_L_FG_t_r + H_L_FG_b_r) / 2
    # solphparams.loc[Tval, 'H_L_FG_share_max'] = H_L_FG_t_r
    # solphparams.loc[Tval, 'Q_CW_min'] = Q_cond_t_r
    solphparams.loc[Tval, 'H_L_FG_share_max'] = H_L
    solphparams.loc[Tval, 'Q_CW_min'] = Q_CW

    print('_____________________________')
    print('#############################')
    print()
    print('Simulationslaufzeit: ', str(elapsed_time))

    # print('_____________________________')
    # print('#############################')
    # print()
    # print('Ergebnisse:')
    # print()
    # print('Q_N: ' + "%.2f" % abs(Q_N/1e6) + " MW")
    # print('Q_in: ' + "%.2f" % (Q_in_t/1e6) + " MW")
    # print('P_max_woDH: ' + "%.2f" % (P_max_woDH/1e6) + " MW")
    # print('P_min_woDH: ' + "%.2f" % (P_min_woDH/1e6) + " MW")
    # print('eta_el_max: ' + "%.4f" % eta_el_max)
    # print('eta_el_min: ' + "%.4f" % eta_el_min)
    # print('H_L_FG_share_max: ' + "%.4f" % H_L_FG_share_max)
    # print('Q_CW_min: ' + "%.2f" % (Q_CW_min/1e6) + " MW")
    # print('beta: ' + "%.4f" % beta)
    # print()
    # print('_____________________________')
    # print('#############################')

with open('ccet_QPdata.json', 'w') as file:
    json.dump(QPjson, file, indent=4)

dir_path = abspath(join(__file__, "../.."))
save_path = join(dir_path, 'Eingangsdaten', 'ccet_parameters.csv')

solphparams.to_csv(save_path, sep=';')

# plant_name = 'GuD'

# df = pd.DataFrame({'plant': [plant_name]*9,
#                    'parameter': ['Q_N', 'Q_in', 'P_max_woDH', 'P_min_woDH',
#                                  'Eta_el_max_woDH', 'Eta_el_min_woDH',
#                                  'H_L_FG_share_max', 'Q_CW_min', 'beta'],
#                    'unit': ['MW', 'MW', 'MW', 'MW', '-', '-', '-', 'MW', '-'],
#                    'value': [abs(Q_N/1e6), Q_in_t/1e6, P_max_woDH/1e6,
#                              P_min_woDH/1e6, eta_el_max, eta_el_min,
#                              H_L_FG_share_max, Q_CW_min/1e6, beta]})

# df.to_csv('data_' + plant_name + '.csv', index=False, sep=";")
