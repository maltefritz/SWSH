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
        User defined JSON parameter file.

    busses : dict
        Busses of the energy system.

    Note
    ----
    Gas source uses the following parameters:
    - 'gas_price' is the constant price of gas in €/MWh
    - 'co2_price' is the constant price of caused emissions in €/MWh
    - 'ef_gas' is the constant emission factor of gas
    """
    gas_source = solph.Source(
        label='Gasquelle',
        outputs={busses['gnw']: solph.Flow(
            variable_costs=(param['param']['gas_price']
                            + (param['param']['co2_price']
                               * param['param']['ef_gas'])))})
    return gas_source
