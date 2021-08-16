# -*- coding: utf-8 -*-
"""
Created on Wed Aug 11 11:04:43 2021

@author: Malte Fritz
"""

import oemof.solph as solph
from help_funcs import liste


def gas_source(param, busses):
    r"""
    Get gas source for Generic Model energy system.

    Parameters
    ----------
    param : dict
        JSON parameter file of user defined constants.

    busses : dict
        Busses of the energy system.

    Note
    ----
    Gas source uses the following parameters:
    - 'gas_price' is the constant price of gas in €/MWh
    - 'co2_price' is the constant price of caused emissions in €/t_co2
    - 'ef_gas' is the constant emission factor of gas in t_co2/MWh

    Topology
    --------
    Input: none

    Output: Gas network (gnw)
    """
    gas_source = solph.Source(
        label='Gasquelle',
        outputs={busses['gnw']: solph.Flow(
            variable_costs=(param['param']['gas_price']
                            + (param['param']['co2_price']
                               * param['param']['ef_gas'])))}
        )
    return gas_source


def electricity_source(param, data, busses):
    r"""
    Get electricity source for Generic Model energy system.

    Parameters
    ----------
    param : dict
        JSON parameter file of user defined constants.

    data : pandas.DataFrame
        csv file of user defined time dependent parameters.

    busses : dict
        Busses of the energy system.

    Note
    ----
    Electricity source uses the following parameters:
    - 'elec_consumer_charges_grid' are the constant consumer charges for
       electricity drawn from the grid in €/MWh
    - 'elec_consumer_charges_self' are the constant consumer charges for
       internal electricity usage in €/MWh
    - 'el_spot_price' is the time series of spot market price in €/MWh
    - 'co2_price' is the constant price of caused emissions in €/t_co2
    - 'ef_om' is the time series of emission factors of overall electricity mix
      in t_co2/MWh

    Topology
    --------
    Input: none

    Output: Electricity network (enw)
    """
    elec_source = solph.Source(
        label='Stromquelle',
        outputs={busses['enw']: solph.Flow(
            variable_costs=(
                param['param']['elec_consumer_charges_grid']
                - param['param']['elec_consumer_charges_self']
                + data['el_spot_price']
                + (param['param']['co2_price']
                   * data['ef_om'])))}
        )
    return elec_source


def solar_thermal_source(param, data, busses):
    r"""
    Get solar thermal source for Generic Model energy system.

    Parameters
    ----------
    param : dict
        JSON parameter file of user defined constants.

    data : pandas.DataFrame
        csv file of user defined time dependent parameters.

    busses : dict
        Busses of the energy system.

    Note
    ----
    Solar thermal source uses the following parameters:
    - 'active' is a binary parameter wether is used or not
    - 'usage' is parameter wether solar thermal is used in high temperature
      network or low temperature network
    - 'op_cost_var' are the variable operational costs in €/MWh
    - 'solar_data_LT' is the time series of low temperature solar thermal heat
      in MWh/m^2
    - 'solar_data_HT' is the time series of high temperature solar thermal heat
      in MWh/m^2

    Topology
    --------
    Input: none

    Output: Solar thermal node (sol_node)
    """
    if param['Sol']['active']:
        if param['Sol']['usage'] == 'LT':
            solar_thermal_source = solph.Source(
                label='Solarthermie',
                outputs={busses['sol_node']: solph.Flow(
                    variable_costs=param['Sol']['op_cost_var'],
                    nominal_value=(
                        max(data['solar_data']) * param['Sol']['A']),
                    fix=data['solar_data'] / max(data['solar_data']))}
                )
        elif param['Sol']['usage'] == 'HT':
            solar_thermal_source = solph.Source(
                label='Solarthermie',
                outputs={busses['sol_node']: solph.Flow(
                    variable_costs=param['Sol']['op_cost_var'],
                    nominal_value=(
                        max(data['solar_data_HT']) * param['Sol']['A']),
                    fix=data['solar_data_HT'] / max(data['solar_data_HT']))}
                )
        return solar_thermal_source


def must_run_source(param, data, busses):
    r"""
    Get must run source for Generic Model energy system.

    Parameters
    ----------
    param : dict
        JSON parameter file of user defined constants.

    data : pandas.DataFrame
        csv file of user defined time dependent parameters.

    busses : dict
        Busses of the energy system.

    Note
    ----
    Must run source uses the following parameters:
    - 'active' is a binary parameter wether is used or not
    - 'type' defines wether it is used constant or time dependent
    - 'op_cost_var' are the variable operational costs in €/MWh
    - 'Q_N' is the constant nominal value in MWh
    - 'Q_MR' is the time series of nominal value in MWh

    Topology
    --------
    Input: none

    Output: High temperature heat network (wnw)
    """
    if param['MR']['active']:
        if param['MR']['type'] == 'constant':
            must_run_source = solph.Source(
                label='Mustrun',
                outputs={busses['wnw']: solph.Flow(
                    variable_costs=param['MR']['op_cost_var'],
                    nominal_value=float(param['MR']['Q_N']),
                    actual_value=1)}
                )
        elif param['MR']['type'] == 'time series':
            must_run_source = solph.Source(
                label='Mustrun',
                outputs={busses['wnw']: solph.Flow(
                    variable_costs=param['MR']['op_cost_var'],
                    nominal_value=1,
                    actual_value=data['Q_MR'])}
                )
    return must_run_source


def electricity_sink(param, data, busses):
    r"""
    Get electricity sink for Generic Model energy system.

    Parameters
    ----------
    param : dict
        JSON parameter file of user defined constants.

    data : pandas.DataFrame
        csv file of user defined time dependent parameters.

    busses : dict
        Busses of the energy system.

    Note
    ----
    Electricity sink uses the following parameters:
    - 'el_spot_price' is the time series of spot market price in €/MWh
    - 'vNNE' is the price for avoided grid usage fees in €/MWh

    Topology
    --------
    Input: Electricity network (enw)

    Output: none
    """
    elec_sink = solph.Sink(
        label='Spotmarkt',
        inputs={busses['enw']: solph.Flow(
            variable_costs=(-data['el_spot_price'] - param['param']['vNNE']))}
        )
    return elec_sink


def ht_emergency_cooling_sink(param, data, busses):
    r"""
    Get heat sink for Generic Model energy system.

    Parameters
    ----------
    param : dict
        JSON parameter file of user defined constants.

    data : pandas.DataFrame
        csv file of user defined time dependent parameters.

    busses : dict
        Busses of the energy system.

    Note
    ----
    Heat sink uses the following parameters:
    - 'heat_price' is the constant price of the heat sold €/MWh
    - 'heat_demand' is the time series of the heat to be covered in MWh
    - 'rel_demand' is a scaling factor for the heat demand

    Topology
    --------
    Input: High temperature heat network (wnw)

    Output: none
    """
    heat_sink = solph.Sink(
        label='Wärmebedarf',
        inputs={busses['wnw']: solph.Flow(
            variable_costs=-param['param']['heat_price'],
            nominal_value=(
                max(data['heat_demand'] * param['param']['rel_demand'])
                ),
            fix=(
                data['heat_demand'] * param['param']['rel_demand']
                / max(data['heat_demand'] * param['param']['rel_demand'])))}
        )
    return heat_sink


def sol_emergency_cooling_sink(param, busses):
    r"""
    Get high temperature emergency cooling sink for Generic Model energy
    system.

    Parameters
    ----------
    param : dict
        JSON parameter file of user defined constants.

    busses : dict
        Busses of the energy system.

    Note
    ----
    High temperature emergency cooling sink uses the following parameters:
    - 'op_cost_var' are the variable operational costs for emergency cooling in
      €/MWh

    Topology
    --------
    Input: High temperature heat network (wnw)

    Output: none
    """
    if param['HT-EC']['active']:
        ht_ec_sink = solph.Sink(
            label='HT-EC',
            inputs={
                busses['wnw']: solph.Flow(
                    variable_costs=param['TES']['op_cost_var'])}
            )
        return ht_ec_sink


def sol_ec_sink(param, data, busses):
    r"""
    Get solar thermal emergency cooling sink for Generic Model energy system.

    Parameters
    ----------
    param : dict
        JSON parameter file of user defined constants.

    data : pandas.DataFrame
        csv file of user defined time dependent parameters.

    busses : dict
        Busses of the energy system.

    Note
    ----
    Solar thermal emergency cooling sink uses the following parameters:
    - 'op_cost_var' are the variable operational costs for emergency cooling in
      €/MWh

    Topology
    --------
    Input: Solar thermal node (sol_node)

    Output: none
    """
    if param['Sol EC']['active']:
        sol_ec_sink = solph.Sink(
            label='Sol EC',
            inputs={['sol_node']: solph.Flow(
                variable_costs=param['TES']['op_cost_var'])}
            )
    return sol_ec_sink


def electric_boiler(param, data, busses):
    r"""
    Get electric boiler for Generic Model energy system.

    Parameters
    ----------
    param : dict
        JSON parameter file of user defined constants.

    data : pandas.DataFrame
        csv file of user defined time dependent parameters.

    busses : dict
        Busses of the energy system.

    Note
    ----
    Electric boiler uses the following parameters:
    - 'active' is a binary parameter wether is used or not
    - 'type' defines wether it is used constant or time dependent
    - 'amount' is the amount of this components installed
    - 'Q_N' is the constant nominal value in MWh
    - 'op_cost_var' are the variable operational costs in €/MWh
    - 'Q_min_rel' is a scaling factor for minimal heat output
    - 'elec_consumer_charges_self' are the constant consumer charges for
       internal electricity usage in €/MWh
    - 'eta' is the conversion factor for energy transformation
    - 'Q_EHK' is the time series of nominal value in MWh

    Topology
    --------
    Input: Electricity network (enw)

    Output: High temperature heat network (wnw)
    """
    if param['EHK']['active']:
        if param['EHK']['type'] == 'constant':
            for i in range(1, param['EHK']['amount']+1):
                ehk = solph.Transformer(
                    label='Elektroheizkessel_' + str(i),
                    inputs={busses['enw']: solph.Flow()},
                    outputs={busses['wnw']: solph.Flow(
                        nominal_value=param['EHK']['Q_N'],
                        max=1,
                        min=param['EHK']['Q_min_rel'],
                        variable_costs=(
                            param['EHK']['op_cost_var']
                            + param['param']['elec_consumer_charges_self']))},
                    conversion_factors={busses['wnw']: param['EHK']['eta']})
        elif param['EHK']['type'] == 'time series':
            for i in range(1, param['EHK']['amount']+1):
                ehk = solph.Transformer(
                    label='Elektroheizkessel_' + str(i),
                    inputs={busses['enw']: solph.Flow()},
                    outputs={busses['wnw']: solph.Flow(
                        nominal_value=1,
                        max=data['Q_EHK'],
                        min=data['Q_EHK'] * param['EHK']['Q_min_rel'],
                        variable_costs=(
                            param['EHK']['op_cost_var']
                            + param['param']['elec_consumer_charges_self']))},
                    conversion_factors={busses['wnw']: param['EHK']['eta']})
                return ehk


def peak_load_boiler(param, data, busses):
    r"""
    Get peak load boiler for Generic Model energy system.

    Parameters
    ----------
    param : dict
        JSON parameter file of user defined constants.

    data : pandas.DataFrame
        csv file of user defined time dependent parameters.

    busses : dict
        Busses of the energy system.

    Note
    ----
    Peak load boiler uses the following parameters:
    - 'active' is a binary parameter wether is used or not
    - 'type' defines wether it is used constant or time dependent
    - 'amount' is the amount of this components installed
    - 'Q_N' is the constant nominal value in MWh
    - 'op_cost_var' are the variable operational costs in €/MWh
    - 'Q_min_rel' is a scaling factor for minimal heat output
    - 'energy_tax' is the tax for the primary energy uses in €/MWh
    - 'eta' is the conversion factor for energy transformation
    - 'Q_SLK' is the time series of nominal value in MWh

    Topology
    --------
    Input: Gas network (gnw)

    Output: High temperature heat network (wnw)
    """
    if param['SLK']['active']:
        if param['SLK']['type'] == 'constant':
            for i in range(1, param['SLK']['amount']+1):
                slk = solph.Transformer(
                    label='Spitzenlastkessel_' + str(i),
                    inputs={busses['gnw']: solph.Flow()},
                    outputs={busses['wnw']: solph.Flow(
                        nominal_value=param['SLK']['Q_N'],
                        max=1,
                        min=param['SLK']['Q_min_rel'],
                        variable_costs=(
                            param['SLK']['op_cost_var']
                            + param['param']['energy_tax']))},
                    conversion_factors={busses['wnw']: param['SLK']['eta']})
        elif param['SLK']['type'] == 'time series':
            for i in range(1, param['SLK']['amount']+1):
                slk = solph.Transformer(
                    label='Spitzenlastkessel_' + str(i),
                    inputs={busses['gnw']: solph.Flow()},
                    outputs={busses['wnw']: solph.Flow(
                        nominal_value=1,
                        max=data['Q_SLK'],
                        min=0,
                        variable_costs=(
                            param['SLK']['op_cost_var']
                            + param['param']['energy_tax']))},
                    conversion_factors={busses['wnw']: param['SLK']['eta']})
                return slk


def internal_combustion_engine(param, data, busses, periods):
    r"""
    Get internal combustion engine for Generic Model energy system.

    Parameters
    ----------
    param : dict
        JSON parameter file of user defined constants.

    data : pandas.DataFrame
        csv file of user defined time dependent parameters.

    busses : dict
        Busses of the energy system.

    periods: int
        Number of time steps of the optimization.

    Note
    ----
    Internal combustion engine uses the following parameters:
    - 'active' is a binary parameter wether is used or not
    - 'type' defines wether it is used constant or time dependent
    - 'amount' is the amount of this components installed
    - 'op_cost_var' are the variable operational costs in €/MWh
    - 'chp_bonus' is the revenue for the electricity sold by chp
    - 'TEHG_bonus' is the revenue for participation in the Emmisions Trading
      Act

    - For specific parameter see documentation of the GenericCHP component in
      oemof solph. Depending on the selected type, the specific parameters are
      used as a constant value or as a time series.

    Topology
    --------
    Input: Gas network (gnw)

    Output: High temperature heat network (wnw), electricity network (enw)
    """
    if param['BHKW']['active']:
        if param['BHKW']['type'] == 'constant':
            for i in range(1, param['BHKW']['amount']+1):
                bhkw = solph.components.GenericCHP(
                    label='BHKW_' + str(i),
                    fuel_input={busses['gnw']: solph.Flow(
                        H_L_FG_share_max=liste(
                            param['BHKW']['H_L_FG_share_max'], periods),
                        H_L_FG_share_min=liste(
                            param['BHKW']['H_L_FG_share_min'], periods),
                        nominal_value=param['BHKW']['Q_in'])},
                    electrical_output={busses['enw']: solph.Flow(
                        variable_costs=(
                            param['BHKW']['op_cost_var']
                            - param['BHKW']['chp_bonus']
                            - param['BHKW']['TEHG_bonus']),
                        P_max_woDH=liste(param['BHKW']['P_max_woDH'], periods),
                        P_min_woDH=liste(param['BHKW']['P_min_woDH'], periods),
                        Eta_el_max_woDH=liste(
                            param['BHKW']['Eta_el_max_woDH'], periods),
                        Eta_el_min_woDH=liste(
                            param['BHKW']['Eta_el_min_woDH'], periods))},
                    heat_output={busses['wnw']: solph.Flow(
                        Q_CW_min=liste(0, periods))},
                    Beta=liste(0, periods),
                    back_pressure=False)
        elif param['BHKW']['type'] == 'time series':
            for i in range(1, param['BHKW']['amount']+1):
                bhkw = solph.components.GenericCHP(
                    label='BHKW_' + str(i),
                    fuel_input={busses['gnw']: solph.Flow(
                        H_L_FG_share_max=data['ICE_H_L_FG_share_max'].tolist(),
                        H_L_FG_share_min=data['ICE_H_L_FG_share_min'].tolist(),
                        nominal_value=data['ICE_Q_in'].mean())},
                    electrical_output={busses['enw']: solph.Flow(
                        variable_costs=(
                            param['BHKW']['op_cost_var']
                            - param['BHKW']['chp_bonus']
                            - param['BHKW']['TEHG_bonus']),
                        P_max_woDH=data['ICE_P_max_woDH'].tolist(),
                        P_min_woDH=data['ICE_P_min_woDH'].tolist(),
                        Eta_el_max_woDH=data['ICE_eta_el_max'].tolist(),
                        Eta_el_min_woDH=data['ICE_eta_el_min'].tolist())},
                    heat_output={busses['wnw']: solph.Flow(
                        Q_CW_min=liste(0, periods))},
                    Beta=liste(0, periods),
                    back_pressure=False)
                return bhkw


def combined_cycle_extraction_turbine(param, data, busses, periods):
    r"""
    Get combined cycle extraction turbine for Generic Model energy system.

    Parameters
    ----------
    param : dict
        JSON parameter file of user defined constants.

    data : pandas.DataFrame
        csv file of user defined time dependent parameters.

    busses : dict
        Busses of the energy system.

    periods: int
        Number of time steps of the optimization.

    Note
    ----
    Combined cycle extraction turbine uses the following parameters:
    - 'active' is a binary parameter wether is used or not
    - 'type' defines wether it is used constant or time dependent
    - 'amount' is the amount of this components installed
    - 'op_cost_var' are the variable operational costs in €/MWh
    - 'chp_bonus' is the revenue for the electricity sold by chp
    - 'TEHG_bonus' is the revenue for participation in the Emmisions Trading
      Act

    - For specific parameter see documentation of the GenericCHP component in
      oemof solph. Depending on the selected type, the specific parameters are
      used as a constant value or as a time series.

    Topology
    --------
    Input: Gas network (gnw)

    Output: High temperature heat network (wnw), electricity network (enw)
    """
    if param['GuD']['active']:
        if param['GuD']['type'] == 'constant':
            for i in range(1, param['GuD']['amount']+1):
                gud = solph.components.GenericCHP(
                    label='GuD_' + str(i),
                    fuel_input={busses['gnw']: solph.Flow(
                        H_L_FG_share_max=liste(
                            param['GuD']['H_L_FG_share_max'], periods),
                        nominal_value=param['GuD']['Q_in'])},
                    electrical_output={busses['enw']: solph.Flow(
                        variable_costs=(
                            param['GuD']['op_cost_var']
                            - param['GuD']['chp_bonus']
                            - param['GuD']['TEHG_bonus']),
                        P_max_woDH=liste(
                            param['GuD']['P_max_woDH'], periods),
                        P_min_woDH=liste(
                            param['GuD']['P_min_woDH'], periods),
                        Eta_el_max_woDH=liste(
                            param['GuD']['Eta_el_max_woDH'], periods),
                        Eta_el_min_woDH=liste(
                            param['GuD']['Eta_el_min_woDH'], periods))},
                    heat_output={busses['wnw']: solph.Flow(
                        Q_CW_min=liste(param['GuD']['Q_CW_min'], periods))},
                    Beta=liste(param['GuD']['beta'], periods),
                    back_pressure=False)
        elif param['GuD']['type'] == 'time series':
            for i in range(1, param['GuD']['amount']+1):
                gud = solph.components.GenericCHP(
                    label='GuD_' + str(i),
                    fuel_input={busses['gnw']: solph.Flow(
                        H_L_FG_share_max=(
                            data['CCET_H_L_FG_share_max'].tolist()),
                        nominal_value=data['CCET_Q_in'].mean())},
                    electrical_output={busses['enw']: solph.Flow(
                        variable_costs=(
                            param['GuD']['op_cost_var']
                            - param['GuD']['chp_bonus']
                            - param['GuD']['TEHG_bonus']),
                        P_max_woDH=data['CCET_P_max_woDH'].tolist(),
                        P_min_woDH=data['CCET_P_min_woDH'].tolist(),
                        Eta_el_max_woDH=data['CCET_eta_el_max'].tolist(),
                        Eta_el_min_woDH=data['CCET_eta_el_min'].tolist())},
                    heat_output={busses['wnw']: solph.Flow(
                        Q_CW_min=data['CCET_Q_CW_min'].tolist())},
                    Beta=data['CCET_beta'].tolist(),
                    back_pressure=False)
                return gud


def back_pressure_turbine(param, data, busses, periods):
    r"""
    Get back pressure turbine for Generic Model energy system.

    Parameters
    ----------
    param : dict
        JSON parameter file of user defined constants.

    data : pandas.DataFrame
        csv file of user defined time dependent parameters.

    busses : dict
        Busses of the energy system.

    periods: int
        Number of time steps of the optimization.

    Note
    ----
    Back pressure turbine uses the following parameters:
    - 'active' is a binary parameter wether is used or not
    - 'type' defines wether it is used constant or time dependent
    - 'amount' is the amount of this components installed
    - 'op_cost_var' are the variable operational costs in €/MWh
    - 'chp_bonus' is the revenue for the electricity sold by chp
    - 'TEHG_bonus' is the revenue for participation in the Emmisions Trading
      Act

    - For specific parameter see documentation of the GenericCHP component in
      oemof solph. Depending on the selected type, the specific parameters are
      used as a constant value or as a time series.

    Topology
    --------
    Input: Gas network (gnw)

    Output: High temperature heat network (wnw), electricity network (enw)
    """
    if param['BPT']['active']:
        if param['BPT']['type'] == 'constant':
            for i in range(1, param['BPT']['amount']+1):
                bpt = solph.components.GenericCHP(
                    label='bpt' + str(i),
                    fuel_input={busses['gnw']: solph.Flow(
                        H_L_FG_share_max=liste(
                            param['bpt']['H_L_FG_share_max'], periods),
                        nominal_value=param['bpt']['Q_in'])},
                    electrical_output={busses['enw']: solph.Flow(
                        variable_costs=(
                            param['bpt']['op_cost_var']
                            - param['bpt']['chp_bonus']
                            - param['bpt']['TEHG_bonus']),
                        P_max_woDH=liste(param['bpt']['P_max_woDH'], periods),
                        P_min_woDH=liste(param['bpt']['P_min_woDH'], periods),
                        Eta_el_max_woDH=liste(
                            param['bpt']['Eta_el_max_woDH'], periods),
                        Eta_el_min_woDH=liste(
                            param['bpt']['Eta_el_min_woDH'], periods))},
                    heat_output={busses['wnw']: solph.Flow(
                        Q_CW_min=liste(0, periods))},
                    Beta=liste(0, periods),
                    back_pressure=True)
        elif param['BPT']['type'] == 'time series':
            for i in range(1, param['BPT']['amount']+1):
                bpt = solph.components.GenericCHP(
                    label='bpt' + str(i),
                    fuel_input={busses['gnw']: solph.Flow(
                        H_L_FG_share_max=data['BPT_H_L_FG_share_max'].tolist(),
                        nominal_value=data['BPT_Q_in'].mean())},
                    electrical_output={busses['enw']: solph.Flow(
                        variable_costs=(
                            param['bpt']['op_cost_var']
                            - param['bpt']['chp_bonus']
                            - param['bpt']['TEHG_bonus']),
                        P_max_woDH=data['BPT_P_max_woDH'].tolist(),
                        P_min_woDH=data['BPT_P_min_woDH'].tolist(),
                        Eta_el_max_woDH=data['BPT_Eta_el_max_woDH'].tolist(),
                        Eta_el_min_woDH=data['BPT_Eta_el_min_woDH'].tolist())},
                    heat_output={busses['wnw']: solph.Flow(
                        Q_CW_min=liste(0, periods))},
                    Beta=liste(0, periods),
                    back_pressure=True)
                return bpt


def ht_heat_pump(param, data, busses):
    r"""
    Get high temperature heat pump for Generic Model energy system.

    Parameters
    ----------
    param : dict
        JSON parameter file of user defined constants.

    data : pandas.DataFrame
        csv file of user defined time dependent parameters.

    busses : dict
        Busses of the energy system.

    Note
    ----
    High temperature heat pump uses the following parameters:
    - 'active' is a binary parameter wether is used or not
    - 'type' defines wether it is used constant or time dependent
    - 'amount' is the amount of this components installed

    - 'P_max' is the constant maximum output power in MW
    - 'P_min' is the constant minimum output power in MW
    - 'c_1' is the linear coefficicient 1 (slope)
    - 'c_0' is the linear coefficicient 0 (y-intersection)

    - 'P_max_hp' is the time series of maximum output power in MW
    - 'P_min_hp' is the time series minimum output power in MW

    - 'elec_consumer_charges_self' are the constant consumer charges for
       internal electricity usage in €/MWh
    - 'op_cost_var' are the variable operational costs in €/MWh

    Topology
    --------
    Input: Electricity network (enw)

    Output: High temperature heat network (wnw)
    """
    if param['HP']['active']:
        if param['HP']['type'] == 'constant':
            for i in range(1, param['HP']['amount']+1):
                ht_hp = solph.components.OffsetTransformer(
                    label='HP_' + str(i),
                    inputs={busses['enw']: solph.Flow(
                        nominal_value=param['HP']['P_max'],
                        max=1,
                        min=param['HP']['P_min'] / param['HP']['P_max'],
                        variable_costs=(
                            param['param']['elec_consumer_charges_self']),
                        nonconvex=solph.NonConvex())},
                    outputs={busses['wnw']: solph.Flow(
                        variable_costs=param['HP']['op_cost_var'])},
                    coefficients=[param['HP']['c_0'], param['HP']['c_1']])
        elif param['HP']['type'] == 'time series':
            for i in range(1, param['HP']['amount']+1):
                ht_hp = solph.components.OffsetTransformer(
                    label='HP_' + str(i),
                    inputs={busses['enw']: solph.Flow(
                        nominal_value=1,
                        max=data['P_max_hp'],
                        min=data['P_min_hp'],
                        variable_costs=(
                            param['param']['elec_consumer_charges_self']),
                        nonconvex=solph.NonConvex())},
                    outputs={busses['wnw']: solph.Flow(
                        variable_costs=param['HP']['op_cost_var'])},
                    coefficients=[data['c_0_hp'], data['c_1_hp']])
                return ht_hp


def lt_heat_pump(param, data, busses):
    r"""
    Get low temperature heat pump for Generic Model energy system.

    Parameters
    ----------
    param : dict
        JSON parameter file of user defined constants.

    data : pandas.DataFrame
        csv file of user defined time dependent parameters.

    busses : dict
        Busses of the energy system.

    Note
    ----
    Low temperature heat pump uses the following parameters:
    - 'active' is a binary parameter wether is used or not
    - 'type' defines wether it is used constant or time dependent
    - 'amount' is the amount of this components installed

    - 'cop' is the constant coefficient of performance

    - 'cop_lthp' is the time series of coefficient of performance

    - 'elec_consumer_charges_self' are the constant consumer charges for
       internal electricity usage in €/MWh
    - 'op_cost_var' are the variable operational costs in €/MWh

    Topology
    --------
    Input: Electricity network (enw), low temperature heat network (lt_wnw)

    Output: High temperature heat network (wnw)
    """
    if param['LT-HP']['active']:
        if param['LT-HP']['type'] == 'constant':
            for i in range(1, param['LT-HP']['amount']+1):
                lt_hp = solph.Transformer(
                    label="LT-HP_" + str(i),
                    inputs={
                        busses['lt_wnw']: solph.Flow(),
                        busses['enw']: solph.Flow(
                            variable_costs=(
                                param['param']['elec_consumer_charges_self'])
                            )},
                    outputs={busses['wnw']: solph.Flow(
                        variable_costs=(
                            param['HP']['op_cost_var']))},
                    conversion_factors={
                        busses['enw']: 1 / param['LT-HP']['cop'],
                        busses['lt_wnw']: ((param['LT-HP']['cop']-1)
                                           / param['LT-HP']['cop'])})
        elif param['LT-HP']['type'] == 'time series':
            for i in range(1, param['LT-HP']['amount']+1):
                lt_hp = solph.Transformer(
                    label="LT-HP_" + str(i),
                    inputs={
                        busses['lt_wnw']: solph.Flow(),
                        busses['enw']: solph.Flow(
                            variable_costs=(
                                param['param']['elec_consumer_charges_self'])
                            )},
                    outputs={busses['wnw']: solph.Flow(
                        variable_costs=(
                            param['HP']['op_cost_var']))},
                    conversion_factors={
                        busses['enw']: 1/data['cop_lthp'],
                        busses['lt_wnw']: (data['cop_lthp']-1)/data['cop_lthp']
                        })
                return lt_hp
