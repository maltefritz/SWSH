# -*- coding: utf-8 -*-
"""
Created on Wed Aug 11 11:04:43 2021

@author: Malte Fritz
"""

import oemof.solph as solph


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
