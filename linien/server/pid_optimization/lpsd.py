# coding=utf-8
import numpy as np

# code taken from https://github.com/conradzim/lpsd
# which is a fork of https://github.com/rudolfbyker/lpsd
# which is a fork of https://github.com/tobin/lpsd


def lpsd(x, windowfcn, fmin, fmax, Jdes, Kdes, Kmin, fs, xi):
    """
    LPSD Power spectrum estimation with a logarithmic frequency axis.

    Estimates the power spectrum or power spectral density of the time series x at JDES frequencies equally spaced (on
    a logarithmic scale) from FMIN to FMAX.

    Originally at: https://github.com/tobin/lpsd
    Translated from Matlab to Python by Rudolf W Byker in 2018.

    The implementation follows references [1] and [2] quite closely; in
    particular, the variable names used in the program generally correspond
    to the variables in the paper; and the corresponding equation numbers
    are indicated in the comments.

    References:
      [1] Michael Tröbs and Gerhard Heinzel, "Improved spectrum estimation
      from digitized time series on a logarithmic frequency axis," in
      Measurement, vol 39 (2006), pp 120-129.
        * http://dx.doi.org/10.1016/j.measurement.2005.10.010
        * http://pubman.mpdl.mpg.de/pubman/item/escidoc:150688:1

      [2] Michael Tröbs and Gerhard Heinzel, Corrigendum to "Improved
      spectrum estimation from digitized time series on a logarithmic
      frequency axis."

    Author(s): Tobin Fricke <tobin.fricke@ligo.org> 2012-04-17

    :param x: time series to be transformed. "We assume to have a long stream x(n), n=0, ..., N-1 of equally spaced
        input data sampled with frequency fs. Typical values for N range from 10^4 to >10^6" - Section 8 of [1]

    :param windowfcn: function handle to windowing function (e.g. @hanning) "Choose a window function w(j, l) to reduce
        spectral leakage within the estimate. ... The computations of the window function will be performed when the
        segment lengths L(j) have been determined." - Section 8 of [1]

    :param fmin: lowest frequency to estimate. "... we propose not to use the first few frequency bins. The first
        frequency bin that yields unbiased spectral estimates depends on the window function used. The bin is given by
        the effective half-width of the window transfer function." - Section 7 of [1].

    :param fmax: highest frequency to estimate

    :param Jdes: desired number of Fourier frequencies. "A typical value for J is 1000" - Section 8 of [1]

    :param Kdes: desired number of averages

    :param Kmin: minimum number of averages

    :param fs: sampling rate

    :param xi: fractional overlap between segments (0 <= xi < 1). See Figures 5 and 6. "The amount of overlap is a
        trade-off between computational effort and flatness of the data weighting." [1]

    :return: Pxx, f, C

        - Pxx: vector of (uncalibrated) power spectrum estimates
        - f: vector of frequencies corresponding to Pxx
        - C: dict containing calibration factors to calibrate Pxx into either power spectral density or power spectrum.

    """

    # Sanity check the input arguments
    if not callable(windowfcn):
        raise TypeError("windowfcn must be callable")
    if not (fmax > fmin):
        raise ValueError("fmax must be greater than fmin")
    if not (Jdes > 0):
        raise ValueError("Jdes must be greater than 0")
    if not (Kdes > 0):
        raise ValueError("Kdes must be greater than 0")
    if not (Kmin > 0):
        raise ValueError("Kmin must be greater than 0")
    if not (Kdes >= Kmin):
        raise ValueError("Kdes must be greater than or equal to Kmin")
    if not (fs > 0):
        raise ValueError("fs must be greater than 0")
    if not (0 <= xi < 1):
        raise ValueError("xi must be: 0 <= xi 1")

    N = len(x)  # Table 1
    jj = np.arange(Jdes, dtype=int)  # Table 1

    if not (fmin >= float(fs) / N):  # Lowest frequency possible
        raise ValueError(
            "The lowest possible frequency is {}, but fmin={}".format(float(fs) / N),
            fmin,
        )
    if not (fmax <= float(fs) / 2):  # Nyquist rate
        raise ValueError(
            "The Nyquist rate is {}, byt fmax={}".format(float(fs) / 2, fmax)
        )

    g = np.log(fmax) - np.log(fmin)  # (12)
    f = fmin * np.exp(jj * g / float(Jdes - 1))  # (13)
    rp = (
        fmin * np.exp(jj * g / float(Jdes - 1)) * (np.exp(g / float(Jdes - 1)) - 1)
    )  # (15)

    # r' now contains the 'desired resolutions' for each frequency bin, given the rule that we want the resolution to be
    # equal to the difference in frequency between adjacent bins. Below we adjust this to account for the minimum and
    # desired number of averages.

    ravg = (float(fs) / N) * (1 + (1 - xi) * (Kdes - 1))  # (16)
    rmin = (float(fs) / N) * (1 + (1 - xi) * (Kmin - 1))  # (17)

    case1 = rp >= ravg  # (18)
    case2 = np.logical_and(rp < ravg, np.sqrt(ravg * rp) > rmin)  # (18)
    case3 = np.logical_not(np.logical_or(case1, case2))  # (18)

    rpp = np.zeros(Jdes)

    rpp[case1] = rp[case1]  # (18)
    rpp[case2] = np.sqrt(ravg * rp[case2])  # (18)
    rpp[case3] = rmin  # (18)

    # r'' contains adjusted frequency resolutions, accounting for the finite length of the data, the constraint of the
    # minimum number of averages, and the desired number of averages.  We now round r'' to the nearest bin of the DFT
    # to get our final resolutions r.
    L = np.around(float(fs) / rpp).astype(int)  # segment lengths (19)
    r = float(fs) / L  # actual resolution (20)
    m = f / r  # Fourier Tranform bin number (7)

    # Allocate space for some results
    Pxx = np.empty(Jdes)
    S1 = np.empty(Jdes)
    S2 = np.empty(Jdes)

    # Loop over frequencies.  For each frequency, we basically conduct Welch's method with the fourier transform length
    # chosen differently for each frequency.
    # TODO: Try to eliminate the for loop completely, since it is unpythonic and slow. Maybe write doctests first...
    for jj in range(len(f)):

        # Calculate the number of segments
        D = int(np.around((1 - xi) * L[jj]))  # (2)
        K = int(np.floor((N - L[jj]) / float(D) + 1))  # (3)

        # reshape the time series so each column is one segment  <-- FIXME: This is not clear.
        a = np.arange(L[jj])
        b = D * np.arange(K)
        ii = a[:, np.newaxis] + b  # Selection matrix
        data = x[ii]  # x(l+kD(j)) in (5)

        # Remove the mean of each segment.
        data -= np.mean(data, axis=0)  # (4) & (5)

        # Compute the discrete Fourier transform
        window = windowfcn(L[jj])  # (5)
        sinusoid = np.exp(
            -2j * np.pi * np.arange(L[jj])[:, np.newaxis] * m[jj] / L[jj]
        )  # (6)
        data = data * (sinusoid * window[:, np.newaxis])  # (5,6)

        # Average the squared magnitudes
        Pxx[jj] = np.mean(np.abs(np.sum(data, axis=0)) ** 2)  # (8)

        # Calculate some properties of the window function which will be used during calibration
        S1[jj] = np.sum(window)  # (23)
        S2[jj] = np.sum(window ** 2)  # (24)

    # Calculate the calibration factors
    C = {"PS": 2.0 / (S1 ** 2), "PSD": 2.0 / (fs * S2)}  # (28)  # (29)

    return Pxx, f, C
