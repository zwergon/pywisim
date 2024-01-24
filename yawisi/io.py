import numpy as np

from struct import pack, unpack
import time

from yawisi.wind_field import WindField
from yawisi import __version__

_TS_BIN_FMT = '<h4l12fl'  # TurbSim binary format


def to_bts(wind_field: WindField, path, uzhub=None, periodic=True):
    """yawisi wind_field to TurbSim-style binary file
    Code modified based on `turbsim` in PyTurbSim:
        https://github.com/lkilcher/pyTurbSim/blob/master/pyts/io/write.py

    Notes
    -----
    * The turbulence must have been generated on a y-z grid (Locations = Grid).
    """
    if path.endswith('.bts'):  # remove file extension, will be added back later
        path = path[:-4]
    # format-specific constants
    intmin = -32768  # minimum integer
    intrng = 65535  # range of integers
    # calculate intermediate parameters
    y = np.sort(np.unique(wind_field.locations.y_array()))
    z = np.sort(np.unique(wind_field.locations.z_array()))
    ny = y.size  # no. of y points in grid
    nz = z.size  # no. of z points in grif
    nt = wind_field.params.n_samples # no. of time steps
    if y.size == 1:
        dy = 0
    else:
        dy = np.mean(y[1:] - y[:-1])  # hopefully will reduce possible errors
    if z.size == 1:
        dz = 0
    else:
        dz = np.mean(z[1:] - z[:-1])  # hopefully will reduce possible errors
    dt = wind_field.params.sample_time  # time step
    if uzhub is None:  # default is center of grid
        zhub = z[z.size // 2]  # halfway up
        uhub = wind_field.get_umean()  # mean of center of grid
    else:
        uhub, zhub = uzhub
    
    # convert pyconturb dataframe to pyturbsim format (3 x ny x nz x nt)
    ts = wind_field.get_uvwt()
    
    # initialize output arrays
    u_minmax = np.empty((3, 2), dtype=np.float32)  # mins and maxs of time series
    u_off = np.empty((3), dtype=np.float32)  # offsets of each time series
    u_scl = np.empty((3), dtype=np.float32)  # scales of each time series
    desc_str = 'generated by YaWiSi v%s, %s.' % (
        __version__,
        time.strftime('%b %d, %Y, %H:%M (%Z)', time.localtime()))  # description
    # calculate the scales and offsets of each time series
    out = np.empty((3, ny, nz, nt), dtype=np.int16)
    for ind in range(3):
        u_minmax[ind] = ts[ind].min(), ts[ind].max()
        if np.isclose(u_minmax[ind][0], u_minmax[ind][1]):
            u_scl[ind] = 1
        else:
            u_scl[ind] = intrng / (u_minmax[ind][1] - u_minmax[ind][0])
        u_off[ind] = intmin - u_scl[ind] * u_minmax[ind, 0]
        out[ind] = (ts[ind] * u_scl[ind] + u_off[ind]).astype(np.int16)
    with open(path + '.bts', 'wb') as fl:
        # write the header
        fl.write(pack(_TS_BIN_FMT,
                      [7, 8][periodic],  # 7 is not periodic, 8 is periodic
                      nz,
                      ny,
                      0,  # assuming 0 tower points below grid
                      nt,
                      dz,
                      dy,
                      dt,
                      uhub,
                      zhub,
                      z[0],
                      u_scl[0],
                      u_off[0],
                      u_scl[1],
                      u_off[1],
                      u_scl[2],
                      u_off[2],
                      len(desc_str)))
        fl.write(desc_str.encode(encoding='UTF-8'))
        # Swap the y and z indices so that fortran-order writing agrees with the file format.
        # Also, we swap the order of z-axis to agree with the file format.
        # Write the data so that the first index varies fastest (F order).
        # The indexes vary in the following order:
        # component (fastest), y-index, z-index, time (slowest).
        fl.write(np.rollaxis(out, 2, 1).tobytes(order='F'))
