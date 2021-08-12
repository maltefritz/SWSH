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
    """
    gas_source = solph.Source(
        label='Gasquelle',
        outputs={busses['gnw']: solph.Flow(
            variable_costs=(param['param']['gas_price']
                            + (param['param']['co2_price']
                               * param['param']['ef_gas'])))})
    return gas_source


def elec_source(param, data, busses):
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
    """
    elec_source = solph.Source(
        label='Stromquelle',
        outputs={busses['enw']: solph.Flow(
            variable_costs=(param['param']['elec_consumer_charges_grid']
                            - param['param']['elec_consumer_charges_self']
                            + data['el_spot_price']
                            + (param['param']['co2_price']
                               * data['ef_om'])))})
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
    """
    if param['Sol']['active']:
        if param['Sol']['usage'] == 'LT':
            solar_thermal_source = solph.Source(
                label='Solarthermie',
                outputs={busses['sol_node']: solph.Flow(
                    variable_costs=param['Sol']['op_cost_var'],
                    nominal_value=(
                        max(data['solar_data']) * param['Sol']['A']),
                    fix=data['solar_data'] / max(data['solar_data']))})
        elif param['Sol']['usage'] == 'HT':
            solar_thermal_source = solph.Source(
                label='Solarthermie',
                outputs={busses['sol_node']: solph.Flow(
                    variable_costs=param['Sol']['op_cost_var'],
                    nominal_value=(
                        max(data['solar_data_HT']) * param['Sol']['A']),
                    fix=data['solar_data_HT'] / max(data['solar_data_HT']))})
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
