"""Algorithm to determine radiation on tilted plane."""
import numpy as np
import pandas as pd


def calculate_radiation(phi=0, lam=0, timezone='UTC', gamma_e=0,
              alpha_e=0, albedo=0, datetime=np.nan,
              e_dir_hor=np.nan, e_diff_hor=np.nan, e_g_hor=np.nan):
    r"""
    Calculate global, direct, diffuse and reflected radiation on a tilted
    plane given the radiation on the horizontal plane following DIN 5034-2.

    Parameters
    ----------
    phi : numeric
        Latitude.

    lam : numeric
        Longitude.

    timezone : str
        Name of the time zone.

    gamma_e : numeric
        Angle of inclination measured from horizontal position.

    alpha_e : numeric
        South exposure: 0° south, 90° east, 180° north, 270° west.

    datetime : np.ndarray/pandas.core.series.Series
        Timestamp, values must be in datetime format.

    e_dir_hor : np.ndarray/pandas.core.series.Series
        Direct radiation on horizontal plane.

    e_diff_hor : np.ndarray/pandas.core.series.Series
        Diffuse radiation on horizontal plane.

    e_g_hor : np.ndarray/pandas.core.series.Series
        Global radiation on horizontal plane.

    Returns
    -------
    e : pandas.core.frame.DataFrame
        Dataframe containing the datetime as well as global, direct (dir),
        diffuse (diff) and reflected (refl) radiation on the tilted plane.
    """

    # transform angles from deg to rad
    phi = phi * np.pi / 180
    lam = lam * np.pi / 180
    gamma_e = gamma_e * np.pi / 180
    alpha_e = alpha_e * np.pi / 180

    # check if length of the input series match
    timesteps = len(datetime)

    if (len(e_dir_hor) != timesteps or
            len(e_diff_hor) != timesteps or
            len(e_g_hor) != timesteps):
        msg = ('The number of elements for all of the input series (datetime, '
               'e_dir_hor, e_diff_hor, e_g_hor) must be identical.')
        raise ValueError(msg)

    # new DataFrame e
    e = pd.DataFrame(datetime, columns=['date'])

    # set datetime with timezone
    if e['date'].dt.tz is None:
        e['date_timezone'] = e['date'].dt.tz_localize(
                timezone, nonexistent='NaT', ambiguous='NaT')
    else:
        e['date_timezone'] = e['date']

    # get datetime in utc time
    e['date_timezone_utc'] = e['date_timezone'].dt.tz_convert('UTC')

    # calculate time difference
    e['td'] = (e['date_timezone'].dt.hour - e['date_timezone_utc'].dt.hour)

    e.loc[e['td'] > 12, 'td'] = 24 - e['td']
    e.loc[e['td'] < -12, 'td'] = 24 + e['td']

    # calculate day of year
    e['doy'] = e['date'].dt.dayofyear

    # number of days in a year
    leap_year = e['date'].dt.is_leap_year
    e['diy'] = np.nan
    e.loc[leap_year == True, 'diy'] = 366
    e.loc[leap_year == False, 'diy'] = 365

    # J' parameter
    j = 360 * e['doy'] / e['diy']
    # sun declination as function of J'
    delta = np.pi / 180 * (
            0.3948 - 23.2559 * np.cos((j + 9.1) * np.pi / 180) -
            0.3915 * np.cos((2 * j + 5.4) * np.pi / 180) -
            0.1764 * np.cos((3 * j + 26) * np.pi / 180)
            )

    # time equation as function of J'
    zgl = (0.0066 + 7.3525 * np.cos((j + 85.9) * np.pi / 180) +
           9.9359 * np.cos((2 * j + 108.9) * np.pi / 180) +
           0.3387 * np.cos((3 * j + 105.2) * np.pi / 180))

    # get mean local time by timezone and local time
    lz = e['date'].dt.hour + e['date'].dt.minute / 60
    moz = lz - e['td'] + 4 * lam * 180 / np.pi / 60

    # calculate real local time woz and hour angle omega
    e['woz'] = moz + zgl / 60
    omega = (12 - e['woz']) * 15 * np.pi / 180

    # calculate sun hight and azimuth
    gamma_s = np.arcsin(np.cos(omega) * np.cos(phi) * np.cos(delta) +
                        np.sin(phi) * np.sin(delta))

    e['alpha_s'] = np.pi

    expr = np.arccos((np.sin(gamma_s) * np.sin(phi) - np.sin(delta)) /
                     (np.cos(gamma_s) * np.cos(phi)))

    e.loc[e['woz'] <= 12, 'alpha_s'] -= expr
    e.loc[e['woz'] > 12, 'alpha_s'] += expr

    # calculation of angle of incidence theta_tilt on tilted plane
    theta_tilt = np.arccos(
            -np.cos(gamma_s) * np.sin(gamma_e) *
            np.cos(e['alpha_s'] - alpha_e) +
            np.sin(gamma_s) * np.cos(gamma_e)
            )

    # calculate radiation on tilted plane
    # direct radiation
    K = np.cos(theta_tilt) / np.sin(gamma_s)

    limit = 10
    K[K > limit] = limit

    e['dir'] = e_dir_hor * K

    e.loc[e['dir'] < 0, 'dir'] = 0

    # diffuse radiation
    F = 1 - (e_diff_hor / e_g_hor) ** 2
    e['diff'] = (e_diff_hor * 0.5 * (1 + np.cos(gamma_e)) *
                 (1 + F * np.sin(gamma_e / 2) ** 3) *
                 (1 + F * np.cos(theta_tilt) ** 2 * np.cos(gamma_s) ** 3))

    e.loc[e['diff'].isna(), 'diff'] = 0

    # reflection from ground
    e['refl'] = e_g_hor * albedo * 0.5 * (1 - np.cos(gamma_e))

    # global radiation on tilted plane
    e['global'] = e['dir'] + e['diff'] + e['refl']

    return e[['date', 'global', 'dir', 'diff', 'refl']]