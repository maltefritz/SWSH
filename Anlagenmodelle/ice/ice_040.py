"""TESPy model of an internal combustion engine for district heating.

Created on Mon Jan  6 10:37:36 2020

@author: Malte Fritz & Jonas Freißmann
"""

from tespy.components import (Sink, Source, Splitter, Merge, Pump,
                              HeatExchanger, HeatExchangerSimple,
                              CombustionEngine)
from tespy.connections import Bus, Ref, Connection
from tespy.networks import Network
from tespy.tools.characteristics import CharLine
from tespy.tools import document_model

from os.path import abspath, join
import numpy as np
import pandas as pd
import matplotlib as mpl
from matplotlib import pyplot as plt


plt.rcParams['pdf.fonttype'] = 42
mpl.rcParams['savefig.bbox'] = 'tight'

# Für das BHKW unseres Referenzsystem Land ist P_N=15MW
# Q_N = abs(float(input('Gib die Nennwärmeleistung in MW ein: ')))*-1e6
Q_N = 75 * -1e6
# %% network

# define full fluid list for the network's variable space
fluid_list = ['Ar', 'N2', 'O2', 'CO2', 'CH4', 'H2O']
# define unit systems and fluid property ranges
nw = Network(fluids=fluid_list, p_unit='bar', T_unit='C',
             p_range=[0.1, 10], T_range=[50, 1200])

# %% components

# sinks & sources
amb = Source('ambient')
sf = Source('fuel')
chbp = Sink('chimney bypass')
ch = Sink('chimney')

cw = Source('cooling water')
pump = Pump('cooling water pump')

cw_split = Splitter('cooling water splitter')
cw_merge = Merge('cooling water merge')
fg_split = Splitter('flue gas splitter')

fgc = HeatExchanger('flue gas cooler')

cons = HeatExchangerSimple('consumer')
cw_out = Sink('cooling water sink')

# combustion engine
ice = CombustionEngine(label='internal combustion engine')

# %% connections

amb_comb = Connection(amb, 'out1', ice, 'in3')
sf_comb = Connection(sf, 'out1', ice, 'in4')
comb_fg = Connection(ice, 'out3', fg_split, 'in1')

fg_fgc = Connection(fg_split, 'out1', fgc, 'in1')
fg_chbp = Connection(fg_split, 'out2', chbp, 'in1')

fgc_ch = Connection(fgc, 'out1', ch, 'in1')

nw.add_conns(sf_comb, amb_comb, comb_fg, fg_fgc, fg_chbp, fgc_ch)

cw_pu = Connection(cw, 'out1', pump, 'in1')
pu_sp = Connection(pump, 'out1', cw_split, 'in1')

sp_ice1 = Connection(cw_split, 'out1', ice, 'in1')
sp_ice2 = Connection(cw_split, 'out2', ice, 'in2')

ice1_m = Connection(ice, 'out1', cw_merge, 'in1')
ice2_m = Connection(ice, 'out2', cw_merge, 'in2')

nw.add_conns(cw_pu, pu_sp, sp_ice1, sp_ice2, ice1_m, ice2_m)

m_fgc = Connection(cw_merge, 'out1', fgc, 'in2')
fgc_cons = Connection(fgc, 'out2', cons, 'in1')
cons_out = Connection(cons, 'out1', cw_out, 'in1')

nw.add_conns(m_fgc, fgc_cons, cons_out)

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
mot = CharLine(x=x, y=y)

# generator efficiency
x = np.array([0.100, 0.345, 0.359, 0.383, 0.410, 0.432, 0.451, 0.504, 0.541,
              0.600, 0.684, 0.805, 1.000, 1.700, 10])
y = np.array([0.976, 0.989, 0.990, 0.991, 0.992, 0.993, 0.994, 0.995, 0.996,
              0.997, 0.998, 0.999, 1.000, 0.999, 0.99]) * - 0.984
gen1 = CharLine(x=x, y=y)
gen2 = CharLine(x=x, y=y)

power = Bus('power')
power.add_comps({'comp': pump, 'char': mot},
                {'comp': ice, 'param': 'P', 'char': gen1})

ice_power = Bus('ice_power')
ice_power.add_comps({'comp': ice, 'param': 'P', 'char': gen2})

heat = Bus('heat')
heat.add_comps({'comp': ice, 'param': 'Q'}, {'comp': fgc})

heat_cond = Bus('heat_cond')

ti = Bus('ti')
ti.add_comps({'comp': ice, 'param': 'TI'})
nw.add_busses(power, heat, ti, ice_power, heat_cond)

# %% component parameters

# pump isentropic efficiency char_line
x = np.array([0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1,
              1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 2.0, 2.1, 2.2, 2.3,
              2.4, 2.5])
y = np.array([0.7, 0.7667, 0.8229, 0.8698, 0.9081, 0.9387, 0.9623, 0.9796,
              0.9913, 0.9979, 1.0, 0.9981, 0.9926, 0.9839, 0.9725, 0.9586,
              0.9426, 0.9248, 0.9055, 0.8848, 0.8631, 0.8405, 0.8171, 0.7932,
              0.7689, 0.7444])
eta_s_char = dict(char_func=CharLine(x, y), param='m')
pump.set_attr(eta_s=0.8, eta_s_char=eta_s_char,
              design=['eta_s'], offdesign=['eta_s_char'])

# ice charachteristics
# thermal input to power
x = np.array([0.50, 0.75, 0.90, 1.00, 1.05])
y = np.array([2.3, 2.18, 2.14, 2.1, 2.15])
tiP_char = dict(char_func=CharLine(x, y))

# heat to power
x = np.array([0.550, 0.660, 0.770, 0.880, 0.990, 1.100])
y = np.array([0.238, 0.219, 0.203, 0.190, 0.180, 0.173])
Q1_char = dict(char_func=CharLine(x, y))
Q2_char = dict(char_func=CharLine(x, y))

# heat loss to power
x = np.array([0.50, 0.7500, 0.90, 1.000, 1.050])
y = np.array([0.32, 0.3067, 0.30, 0.295, 0.293])
Qloss_char = dict(char_func=CharLine(x, y))


# set combustion chamber fuel, air to stoichometric air ratio and thermal input
ice.set_attr(pr1=0.98, lamb=1.0, design=['pr1'], offdesign=['zeta1'],
             tiP_char=tiP_char, Q1_char=Q1_char, Q2_char=Q2_char,
             Qloss_char=Qloss_char)

# flue gas cooler

x1 = np.array([0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1, 1.1, 1.2,
               1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 2, 2.1, 2.2, 2.3, 2.4, 2.5])
y1 = np.array([0.000, 0.164, 0.283, 0.389, 0.488, 0.581, 0.670, 0.756, 0.840,
               0.921, 1.000, 1.078, 1.154, 1.228, 1.302, 1.374, 1.446, 1.516,
               1.585, 1.654, 1.722, 1.789, 1.855, 1.921, 1.986, 2.051])
x2 = np.array([0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1, 1.1, 1.2,
               1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 2, 2.1, 2.2, 2.3, 2.4, 2.5])
y2 = np.array([0.000, 0.245, 0.375, 0.480, 0.572, 0.655, 0.732, 0.804, 0.873,
               0.938, 1.000, 1.060, 1.118, 1.174, 1.228, 1.281, 1.332, 1.382,
               1.431, 1.479, 1.526, 1.572, 1.618, 1.662, 1.706, 1.749])

kA_char1 = dict(char_func=CharLine(x1, y1), param='m')
kA_char2 = dict(char_func=CharLine(x2, y2), param='m')

fgc.set_attr(pr1=0.99, pr2=0.99,
             kA_char1=kA_char1, kA_char2=kA_char2,
             design=['pr1', 'pr2'], offdesign=['zeta1', 'zeta2', 'kA_char'])

# consumer

cons.set_attr(pr=0.99)

# %% connection parameters


# air and fuel
amb_comb.set_attr(p=1.05, T=20, fluid={'Ar': 0.0129, 'N2': 0.7553, 'H2O': 0,
                                       'CH4': 0, 'CO2': 0.0004, 'O2': 0.2314})
sf_comb.set_attr(T=20, fluid={'CO2': 0, 'Ar': 0, 'N2': 0,
                              'O2': 0, 'H2O': 0, 'CH4': 1})

# flue gas outlet
# m_fgc.set_attr(T=75, design=['T'])
fgc_ch.set_attr(T=150, design=['T'])
fg_chbp.set_attr(m=0)

# cooling water cylce
cw_pu.set_attr(p=10, T=50,
               fluid={'CO2': 0, 'Ar': 0, 'N2': 0, 'O2': 0, 'H2O': 1, 'CH4': 0})

fgc_cons.set_attr(T=90, fluid0={'H2O': 1})
# splitting mass flow in half
sp_ice1.set_attr(m=Ref(sp_ice2, 1, 0))

# cycle closing
cons_out.set_attr(p=Ref(cw_pu, 1, 0), h=Ref(cw_pu, 1, 0))

# %% solving
heat.set_attr(P=Q_N)
# ice.set_attr(P=-1e6)

mode = 'design'
nw.solve(mode=mode)  # , init_path='ice_design')
nw.print_results()
nw.save('ice_design')
print(power.P.val, heat.P.val,
      -power.P.val / ti.P.val, -heat.P.val / ti.P.val)

Q_in = ti.P.val

ice_P_design = ice.P.val

ice.set_attr(P=ice_P_design)
heat.set_attr(P=np.nan)

mode = 'offdesign'
nw.solve(mode=mode, design_path='ice_design')
nw.print_results()
# P_L += [abs(power.P.val)]
# Q_L += [abs(heat.P.val)]

# T_range = [*range(64, 67)]
T_range = [*range(64, 125)]
solphparams = pd.DataFrame(columns=['P_max_woDH', 'eta_el_max',
                                    'P_min_woDH', 'eta_el_min',
                                    'H_L_FG_share_max', 'H_L_FG_share_min'])

for Tval in T_range:
    P_L = []
    Q_L = []

    fgc_cons.set_attr(T=Tval)

#############################
    # Bei P_max: Q_max zu Q_min

    print('Open bypass, shut down flue gas cooler at maximum power output')

    m_bypass = [0, 1/3, 1, 3, 10, 30]
    fg_chbp.set_attr(m=np.nan)
    fgc_ch.set_attr(m=np.nan)

    for m in m_bypass:
        fg_chbp.set_attr(m=Ref(fgc_ch, m, 0))
        nw.solve(mode=mode, design_path='ice_design')
        print(power.P.val, heat.P.val,
              -power.P.val / ti.P.val, -heat.P.val / ti.P.val)
        P_L += [abs(power.P.val)]
        Q_L += [abs(heat.P.val)]
        print(fg_chbp.T.val)

    # # close main chimney
    # fg_chbp.set_attr(m=np.nan)
    # fgc_ch.set_attr(m=np.nan)
    # fgc_ch.set_attr(m=0.01)
    # nw.solve(mode=mode, design_path='ice_design')
    # print(power.P.val, heat.P.val,
    #       -power.P.val / ti.P.val, -heat.P.val / ti.P.val)
    # P_L += [abs(power.P.val)]
    # Q_L += [abs(heat.P.val)]

    P_max_woDH = np.mean(P_L)
    print(P_L)
    eta_el_max_woDH = P_max_woDH / ti.P.val
    H_L_FG_max_tr = 1 - (P_L[0] + Q_L[0]) / ti.P.val
    H_L_FG_min_tl = 1 - (P_L[-1] + Q_L[-1]) / ti.P.val

    ##############################
    # min Q (Opened Bypass), from P_max to P_min
    print('Opened bypass, go from minimum to maximum power')

    ice_power_range = np.linspace(ice_P_design * 0.5, ice_P_design, 7,
                                  endpoint=False)
    fg_chbp.set_attr(m=np.nan)
    fgc_ch.set_attr(m=np.nan)

    fgc_ch.set_attr(m=0.01)

    for P in ice_power_range[::-1]:
        ice.set_attr(P=P)
        nw.solve(mode=mode, design_path='ice_design')
        print(power.P.val, heat.P.val,
              -power.P.val / ti.P.val, -heat.P.val / ti.P.val)
        P_L += [abs(power.P.val)]
        Q_L += [abs(heat.P.val)]

    H_L_FG_min_bl = 1 - (P_L[-1] + Q_L[-1]) / ti.P.val

    ##############################
    # Bei P_min: Q_min to Q_max
    print(fg_chbp.m.val_SI/fgc_ch.m.val_SI)
    print('Open bypass, shut down flue gas cooler at minimum power output')

    ice.set_attr(P=ice_P_design * 0.5)  # Pmin als 0.5*Pmax hardcodet?
    m_bypass = np.linspace(0, fg_chbp.m.val_SI, 7, endpoint=False)[::-1]

    fg_chbp.set_attr(m=np.nan)
    fgc_ch.set_attr(m=np.nan)

    for m in m_bypass:
        fg_chbp.set_attr(m=m)
        nw.solve(mode=mode, design_path='ice_design')
        print(power.P.val, heat.P.val,
              -power.P.val / ti.P.val, -heat.P.val / ti.P.val)
        P_L += [abs(power.P.val)]
        Q_L += [abs(heat.P.val)]

    P_min_woDH = np.mean(P_L[-7:])
    eta_el_min_woDH = P_min_woDH / ti.P.val
    H_L_FG_max_br = 1 - (P_L[-1] + Q_L[-1]) / ti.P.val

    ##############################
    # max Q (Closed Bypass), from min P to max P
    print('Closed bypass, go from minimum to maximum power')

    fg_chbp.set_attr(m=np.nan)
    fgc_ch.set_attr(m=np.nan)

    fg_chbp.set_attr(m=0)

    for P in ice_power_range[1:]:
        ice.set_attr(P=P)
        nw.solve(mode=mode, design_path='ice_design')
        print(power.P.val, heat.P.val,
              -power.P.val / ti.P.val, -heat.P.val / ti.P.val)
        P_L += [abs(power.P.val)]
        Q_L += [abs(heat.P.val)]

    # skip simulation necessary for numeric stability
    if Tval < 65:
        continue

    H_L_FG_max = np.mean([H_L_FG_max_tr, H_L_FG_max_br])
    H_L_FG_min = np.mean([H_L_FG_min_tl, H_L_FG_min_bl])

    solphparams.loc[Tval, 'Q_in'] = Q_in/1e6
    solphparams.loc[Tval, 'P_max_woDH'] = P_max_woDH/1e6
    solphparams.loc[Tval, 'eta_el_max'] = eta_el_max_woDH
    solphparams.loc[Tval, 'P_min_woDH'] = P_min_woDH/1e6
    solphparams.loc[Tval, 'eta_el_min'] = eta_el_min_woDH
    solphparams.loc[Tval, 'H_L_FG_share_max'] = H_L_FG_max
    solphparams.loc[Tval, 'H_L_FG_share_min'] = H_L_FG_min

    # P_Q_Diagramm
    fig, ax = plt.subplots()

    ax.plot(Q_L, P_L, 'x')

    ax.grid(linestyle='--')
    ax.set_xlabel(r'Wärmestrom $\dotQ$')
    ax.set_ylabel('El. Leistung P')
    ax.set_title(r'Betriebsfeld bei $T_{VL}$ = ' + str(Tval) + ' °C')
    plt.show()

dir_path = abspath(join(__file__, "..\\..\\.."))
save_path = join(dir_path, 'Eingangsdaten', 'ice_parameters.csv')

solphparams.to_csv(save_path, sep=';')
