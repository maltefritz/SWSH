# -*- coding: utf-8 -*-
"""
Created on Fri Aug  6 13:26:11 2021

@author: Malte Fritz
"""

from sys import exit


def liste(parameter, periods):
    """Get timeseries list of parameter for solph components."""
    return [parameter for p in range(0, periods)]


def topology_check(param):
    """Check chosen topology for validity:
        - LT-NW
        - wird noch mehr kommen
        """
    if (param['LT-HP']['active']
        and not param['Sol']['active']
        and not param['TES']['active']):
        print("WARNING: You can't have the low temp heat pump active without ",
              "using either the TES or solar heat.")
        exit()
    elif (not param['LT-HP']['active']
          and (param['Sol']['active']
          or param['TES']['active'])):
        print("WARNING: You can't use TES or solar heat without using the low ",
              "temp heat pump.")
        exit()


def result_labelling(dataframe, labeldict):
    """Change columns names of result dataframes."""
    for col in dataframe.columns:
        if col in labeldict:
            dataframe.rename(columns={col: labeldict[col]}, inplace=True)
        else:
            print(col, ' not in labeldict')
