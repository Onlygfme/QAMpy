from __future__ import division, print_function
import numpy as np
from .utils import cabssquared
from .theory import  calculate_MQAM_symbols, calculate_MQAM_scaling_factor
from .equalisation import quantize as quantize_pyx
try:
    import arrayfire as af
except ImportError:
    af = None

def quantize(signal, symbols, method="pyx", **kwargs):
    if method == "pyx":
        return quantize_pyx(signal, symbols, **kwargs)
    elif method == "af":
        if af == None:
            raise RuntimeError("Arrayfire was not imported so cannot use this method for quantization")
        return quantize_af(signal, symbols, **kwargs)
    else:
        raise ValueError("method '%s' unknown has to be either 'pyx' or 'af'"%(method))


def quantize_af(signal, symbols, precision=16):
    global  NMAX
    if precision == 16:
        prec_dtype = np.complex128
    elif precision == 8:
        prec_dtype = np.complex64
    else:
        raise ValueError("Precision has to be either 16 for double complex or 8 for single complex")
    Nmax = NMAX//len(symbols.flatten())//16
    L = signal.flatten().shape[0]
    sig = af.np_to_af_array(signal.flatten().astype(prec_dtype))
    sym = af.transpose(af.np_to_af_array(symbols.flatten().astype(prec_dtype)))
    tmp = af.constant(0, L, dtype=af.Dtype.c64)
    if L < Nmax:
        v, idx = af.imin(af.abs(af.broadcast(lambda x,y: x-y, sig,sym)), dim=1)
        tmp = af.transpose(sym)[idx]
    else:
        steps = L//Nmax
        rem = L%Nmax
        for i in range(steps):
            v, idx = af.imin(af.abs(af.broadcast(lambda x,y: x-y, sig[i*Nmax:(i+1)*Nmax],sym)), dim=1)
            tmp[i*Nmax:(i+1)*Nmax] = af.transpose(sym)[idx]
        v, idx = af.imin(af.abs(af.broadcast(lambda x,y: x-y, sig[steps*Nmax:],sym)), dim=1)
        tmp[steps*Nmax:] = af.transpose(sym)[idx]
    return np.array(tmp)


def normalise_sig(sig, M):
    """Normalise signal to average power"""
    norm = np.sqrt(calS0(sig, M))
    return 1 / norm, sig / norm


def cal_blind_evm(sig, M):
    """Blind calculation of the linear Error Vector Magnitude for an M-QAM
    signal. Does not consider Symbol errors.

    Parameters
    ----------
    sig : array_like
        input signal
    M : int
       QAM order

    Returns
    -------
    evm : float
        Error Vector Magnitude
    """
    ideal = calculate_MQAM_symbols(M).flatten()
    Ai, Pi = normalise_sig(ideal, M)
    Am, Pm = normalise_sig(sig, M)
    evm = np.mean(np.min(abs(Pm[:,np.newaxis].real-Pi.real)**2 +\
            abs(Pm[:,np.newaxis].imag-Pi.imag)**2, axis=1))
    evm /= np.mean(abs(Pi)**2)
    return np.sqrt(evm)


def cal_evm_known_data(sig, ideal, M):
    """Blind calculation of the linear Error Vector Magnitude for an M-QAM
    signal. This function calculates the EVM while calculating longer distances if
    there are symbol errors.

    Parameters
    ----------
    sig : array_like
        input signal
    ideal : array_like
        the error-free signal
    M : int
       QAM order

    Returns
    -------
    evm : float
        Error Vector Magnitude
    """
    Ai, Pi = normalise_sig(ideal, M)
    As, Ps = normalise_sig(sig, M)
    evm = np.mean(abs(Pi.real - Ps.real)**2 + \
                  abs(Pi.imag - Ps.imag)**2)
    evm /= np.mean(abs(Pi)**2)
    return np.sqrt(evm)


def cal_SNR_QAM(E, M):
    """Calculate the signal to noise ratio SNR according to formula given in
    Gao and Tepedelenlioglu in IEEE Trans in Signal Processing Vol 53,
    pg 865 (2005).

    Parameters:
    ----------
    E   : array_like
      input field
    M:  : int
      order of the QAM constallation

    Returns:
    -------
    S0/N: : float
        linear SNR estimate
    """
    gamma = _cal_gamma(M)
    r2 = np.mean(abs(E)**2)
    r4 = np.mean(abs(E)**4)
    S1 = 1 - 2 * r2**2 / r4 - np.sqrt(
        (2 - gamma) * (2 * r2**4 / r4**2 - r2**2 / r4))
    S2 = gamma * r2**2 / r4 - 1
    return S1 / S2


def _cal_gamma(M):
    """Calculate the gamma factor for SNR estimation."""
    A = abs(calculate_MQAM_symbols(M)) / np.sqrt(calculate_MQAM_scaling_factor(M))
    uniq, counts = np.unique(A, return_counts=True)
    return np.sum(uniq**4 * counts / M)


def cal_Q_16QAM(E):
    """Calculate the signal to noise ratio SNR according to formula given in
    Gao and Tepedelenlioglu in IEEE Trans in Signal Processing Vol 53,
    pg 865 (2005).

    Parameters:
    ----------
    E  : array_like
       input field

    Returns:
    --------
    S0/N   : float
         linear SNR estimate
    """
    return cal_SNR_QAM(E, 16)


def calS0(E, M):
    """Calculate the signal power S0 according to formula given in
    Gao and Tepedelenlioglu in IEEE Trans in Signal Processing Vol 53,
    pg 865 (2005).

    Parameters:
    ----------
    E   : array_like
      input field
    M:  : int

    Returns:
    -------
    S0   : float
       signal power estimate
    """
    N = len(E)
    gamma = _cal_gamma(M)
    r2 = np.mean(abs(E)**2)
    r4 = np.mean(abs(E)**4)
    S1 = 1 - 2 * r2**2 / r4 - np.sqrt(
        (2 - gamma) * (2 * r2**4 / r4**2 - r2**2 / r4))
    S2 = gamma * r2**2 / r4 - 1
    # S0 = r2/(1+S2/S1) because r2=S0+N and S1/S2=S0/N
    return r2 / (1 + S2 / S1)


def SNR_QPSK_blind(E):
    """
    Calculates the SNR of a QPSK signal based on the variance of the constellation
    assmuing no symbol errors"""
    E4 = -E**4
    Eref = E4**(1. / 4)
    #P = np.mean(abs(Eref**2))
    P = np.mean(cabssquared(Eref))
    var = np.var(Eref)
    SNR = 10 * np.log10(P / var)
    return SNR


def cal_ser_QAM(data_rx, symbol_tx, M, method="pyx"):
    """
    Calculate the symbol error rate

    Parameters
    ----------

    data_rx : array_like
            received signal
    symbols_tx : array_like
            original symbols
    M       : int
            QAM order

    method : string
       method to use for quantization (either af for arrayfire or pyx for cython)

    Returns
    -------
    SER : float
       Symbol error rate estimate
    """
    data_demod = quantize(data_rx, M, method)
    return np.count_nonzero(data_demod - symbol_tx) / len(data_rx)
