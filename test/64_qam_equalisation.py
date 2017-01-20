import numpy as np
import matplotlib.pylab as plt
from dsp import signals, equalisation, modulation
from dsp.signal_quality import cal_blind_evm



def H_PMD(theta, t, omega): #see Ip and Kahn JLT 25, 2033 (2007)
    """"""
    h1 = np.array([[np.cos(theta), -np.sin(theta)], [np.sin(theta), np.cos(theta)]])
    h2 = np.array([[np.exp(1.j*omega*t/2), np.zeros(len(omega))],[np.zeros(len(omega)), np.exp(-1.j*omega*t/2)]])
    h3 = np.array([[np.cos(theta), np.sin(theta)], [-np.sin(theta), np.cos(theta)]])
    H = np.einsum('ij,jkl->ikl', h1, h2)
    H = np.einsum('ijl,jk->ikl', H, h3)
    return H

def rotate_field(theta, field):
    h = np.array([[np.cos(theta), -np.sin(theta)], [np.sin(theta), np.cos(theta)]])
    return np.dot(h, field)

def applyPMD(field, H):
    Sf = np.fft.fftshift(np.fft.fft(np.fft.fftshift(field, axes=1),axis=1), axes=1)
    SSf = np.einsum('ijk,ik -> ik',H , Sf)
    SS = np.fft.fftshift(np.fft.ifft(np.fft.fftshift(SSf, axes=1),axis=1), axes=1)
    return SS

fb = 40.e9
os = 2
fs = os*fb
N = 10**6
theta = np.pi/2.35
M = 64
QAM = modulation.QAMModulator(M)
snr = 25
muCMA = 8e-3
muRDE = 1.e-3
ntaps = 7
t_pmd = 20.e-12
#Ncma = N//4//os -int(1.5*ntaps)
Ncma = 40000
Nrde = 4*N//5//os -int(1.5*ntaps)

X, Xsymbols, Xbits = QAM.generateSignal(N, snr,  baudrate=fb, samplingrate=fs, PRBSorder=15)
Y, Ysymbols, Ybits = QAM.generateSignal(N, snr, baudrate=fb, samplingrate=fs, PRBSorder=23)

omega = 2*np.pi*np.linspace(-fs/2, fs/2, N*os, endpoint=False)

H = H_PMD(theta, t_pmd, omega)
H2 = H_PMD(-theta, -t_pmd, omega)

S = np.vstack([X,Y])

SS = applyPMD(S, H)

E_m, wx_m, wy_m, err_m, err_rde_m = equalisation.FS_MCMA_MRDE(SS, Ncma, Nrde, ntaps, os, muCMA, muRDE, M)
E_s, wx_s, wy_s, err_s, err_rde_s = equalisation.FS_MCMA_SBD(SS, Ncma, Nrde, ntaps, os, muCMA, muRDE, M)
E, wx, wy, err, err_rde = equalisation.FS_MCMA_MDDMA(SS, Ncma, Nrde, ntaps, os, muCMA, muRDE, M)
#E, wx, wy, err, err_rde = equalisation.FS_CMA_RDE(SS, Ncma, Nrde, ntaps, os, muCMA, muRDE, M)
print("equalised")


evmX = cal_blind_evm(X[::2], M)
evmY = cal_blind_evm(Y[::2], M)
evmEx = cal_blind_evm(E[0], M)
evmEy = cal_blind_evm(E[1], M)
evmEx_m = cal_blind_evm(E_m[0], M)
evmEy_m = cal_blind_evm(E_m[1], M)
evmEx_s = cal_blind_evm(E_s[0], M)
evmEy_s = cal_blind_evm(E_s[1], M)

#sys.exit()
plt.figure()
plt.subplot(221)
plt.title('Recovered MCMA/MDDMA')
plt.plot(E[0].real, E[0].imag, 'r.' ,label=r"$EVM_x=%.1f\%%$"%(evmEx*100))
plt.plot(E[1].real, E[1].imag, 'g.', label=r"$EVM_y=%.1f\%%$"%(100*evmEy))
plt.legend()
plt.subplot(222)
plt.title('Recovered MCMA/MRDE')
plt.plot(E_m[1].real, E_m[1].imag, 'g.', label=r"$EVM_y=%.1f\%%$"%(100*evmEy_m))
plt.plot(E_m[0].real, E_m[0].imag, 'r.' ,label=r"$EVM_x=%.1f\%%$"%(evmEx_m*100))
plt.legend()
plt.subplot(223)
plt.title('Recovered MCMA/SBD')
plt.plot(E_s[1].real, E_s[1].imag, 'g.', label=r"$EVM_y=%.1f\%%$"%(100*evmEy_s))
plt.plot(E_s[0].real, E_s[0].imag, 'r.' ,label=r"$EVM_x=%.1f\%%$"%(evmEx_s*100))
plt.legend()
plt.subplot(224)
plt.title('Original')
plt.plot(X[::2].real, X[::2].imag, 'r.', label=r"$EVM_x=%.1f\%%$"%(100*evmX))
plt.plot(Y[::2].real, Y[::2].imag, 'g.', label=r"$EVM_y=%.1f\%%$"%(100*evmY))
plt.legend()

plt.figure()
plt.subplot(331)
plt.title('CMA/MDDMA Taps')
plt.plot(wx[0,:], 'r')
plt.plot(wx[1,:], '--r')
plt.plot(wy[0,:], 'g')
plt.plot(wy[1,:], '--g')
plt.subplot(332)
plt.title('CMA/MDDMA error cma')
plt.plot(abs(err[0]), color='r')
plt.plot(abs(err[1])- 10, color='g')
plt.subplot(333)
plt.title('CMA/MDDMA error MDDMA')
plt.plot(abs(err_rde[0]), color='r')
plt.plot(abs(err_rde[1])-10, color='g')
plt.subplot(334)
plt.title('MCMA/MRDE Taps')
plt.plot(wx_m[0,:], 'r')
plt.plot(wx_m[1,:], '--r')
plt.plot(wy_m[0,:], 'g')
plt.plot(wy_m[1,:], '--g')
plt.subplot(335)
plt.title('MCMA/MRDE error cma')
plt.plot(abs(err_m[0]), color='r')
plt.plot(abs(err_m[1])- 10, color='g')
plt.subplot(336)
plt.title('MCMA/MRDE error rde')
plt.plot(abs(err_rde_m[0]), color='r')
plt.plot(abs(err_rde_m[1])-10, color='g')
plt.subplot(337)
plt.title('MCMA/SBD Taps')
plt.plot(wx_s[0,:], 'r')
plt.plot(wx_s[1,:], '--r')
plt.plot(wy_s[0,:], 'g')
plt.plot(wy_s[1,:], '--g')
plt.subplot(338)
plt.title('MCMA/SBD error cma')
plt.plot(abs(err_s[0]), color='r')
plt.plot(abs(err_s[1])- 10, color='g')
plt.subplot(339)
plt.title('MCMA/SBD error rde')
plt.plot(abs(err_rde_s[0]), color='r')
plt.plot(abs(err_rde_s[1])-10, color='g')
plt.show()


