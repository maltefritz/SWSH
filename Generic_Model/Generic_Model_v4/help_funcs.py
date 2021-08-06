# -*- coding: utf-8 -*-
"""
Created on Fri Aug  6 13:26:11 2021

@author: Malte Fritz
"""


def liste(parameter, periods):
    """Get timeseries list of parameter for solph components."""
    return [parameter for p in range(0, periods)]


def result_labelling(dataframe, labeldict):
    """Change columns names of result dataframes."""
    for col in dataframe.columns:
        if col in labeldict:
            dataframe.rename(columns={col: labeldict[col]}, inplace=True)
        else:
            print(col, ' not in labeldict')
