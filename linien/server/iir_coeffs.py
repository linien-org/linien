# Copyright 2014-2015 Robert Jordens <jordens@gmail.com>
#
# This file is part of redpid.
#
# redpid is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# redpid is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with redpid.  If not, see <http://www.gnu.org/licenses/>.

from math import log2, ceil, pi
import warnings

import scipy.signal


def make_filter(name, k=1., f=0., g=1e20, q=.5):
    f *= pi

    if name == "LP": # k/(s + 1)
        b = [f*k/(f + 2), f*k/(f + 2)]
        a = [1, (f - 2)/(f + 2)]

    elif name == "HP": # k/(1 + 1/s)
        b = [2*k/(f + 2), 2*k/(-f - 2)]
        a = [1, (f - 2)/(f + 2)]

    elif name == "AP": # k*(s - 1)/(s + 1)
        b = [k*(-f + 2)/(f + 2), -k]
        a = [1, (f - 2)/(f + 2)]

    elif name == "I": # k/s
        b = [f*k/2, f*k/2]
        a = [1, -1]

    elif name == "PI": # k*(s + 1)/(s + 1/g)
        b = [g*k*(f + 2)/(f + 2*g), g*k*(f - 2)/(f + 2*g)]
        a = [1, (f - 2*g)/(f + 2*g)]

    elif name == "P": # k
        b = [k]
        a = [1]

    elif name == "PD": # k*(s + 1)/(1 + s/g)
        b = [g*k*(f + 2)/(f*g + 2), g*k*(f - 2)/(f*g + 2)]
        a = [1, (f*g - 2)/(f*g + 2)]

    elif name == "LP2": # k/(s**2 + 1 + s/q)
        b = [f**2*k*q/(f**2*q + 2*f + 4*q), 2*f**2*k*q/(f**2*q + 2*f + 4*q),
                f**2*k*q/(f**2*q + 2*f + 4*q)]
        a = [1, 2*q*(f**2 - 4)/(f**2*q + 2*f + 4*q),
                (f**2*q - 2*f + 4*q)/(f**2*q + 2*f + 4*q)]

    elif name == "HP2": # k/(1 + s**(-2) + 1/(q*s))
        b = [4*k*q/(f**2*q + 2*f + 4*q), 8*k*q/(-f**2*q - 2*f - 4*q),
                4*k*q/(f**2*q + 2*f + 4*q)]
        a = [1, 2*q*(f**2 - 4)/(f**2*q + 2*f + 4*q),
                (f**2*q - 2*f + 4*q)/(f**2*q + 2*f + 4*q)]

    elif name == "NOTCH": # k*(s**2 + 1)/(s**2 + 1 + s/q)
        b = [k*q*(f**2 + 4)/(f**2*q + 2*f + 4*q),
                2*k*q*(f**2 - 4)/(f**2*q + 2*f + 4*q),
                k*q*(f**2 + 4)/(f**2*q + 2*f + 4*q)]
        a = [1, 2*q*(f**2 - 4)/(f**2*q + 2*f + 4*q),
                (f**2*q - 2*f + 4*q)/(f**2*q + 2*f + 4*q)]

    elif name == "IHO": # 4*k*(s + 1/s + 1/q)/((1 + s/g)*(f*g + 2))
        b = [2*g*k*(f**2*q + 2*f + 4*q)/(q*(f**2*g**2 + 4*f*g + 4)),
                4*g*k*(f**2 - 4)/(f**2*g**2 + 4*f*g + 4),
                2*g*k*(f**2*q - 2*f + 4*q)/(q*(f**2*g**2 + 4*f*g + 4))]
        a = [1, 4/(-f*g - 2), (-f*g + 2)/(f*g + 2)]

    return b, a


def quantize_filter(b, a, shift=None, width=25):
    b, a = [i/a[0] for i in b], [i/a[0] for i in a]

    if shift is None:
        shift = width
        for i in b + a:
            m = ceil(log2(abs(i)))
            if i > 0 and int(m) == m:
                m += 1
            shift = min(shift, int(width - 1 - m))
    s = 1 << shift
    
    b = [int(round(i*s)) for i in b]
    a = [int(round(i*s)) for i in a]

    m = 1<<(width - 1)
    for i in b + a:
        assert -m <= i < m, (hex(i), hex(m))

    z, p, k = scipy.signal.tf2zpk(b, a)
    if any(abs(_) > 1 for _ in p):
        warnings.warn("unstable filter: z={}, p={}, k={}".format(
            z, p, k), RuntimeWarning)

    return b, a, shift


def get_params(b, a, shift=None, width=25, interval=1):
    b, a, shift = quantize_filter(b, a, shift, width)
    params = {}
    for i, (ai, bi) in enumerate(zip(a, b)):
        params["a%i" % i] = int(-ai)
        params["b%i" % i] = int(bi)
    del params["a0"]
    #params["shift"] = shift
    return b, a, params
