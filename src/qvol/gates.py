"""Single- and two-qubit gates as plain NumPy matrices."""
import numpy as np

CNOT = np.array([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, 1], [0, 0, 1, 0]], complex)
X = np.array([[0, 1], [1, 0]], complex)
Y = np.array([[0, -1j], [1j, 0]], complex)
Z = np.array([[1, 0], [0, -1]], complex)


def ry(a):
    c, s = np.cos(a / 2), np.sin(a / 2)
    return np.array([[c, -s], [s, c]], complex)


def rz(a):
    return np.diag([np.exp(-1j * a / 2), np.exp(1j * a / 2)])


def u3(theta, phi, lam):
    """Qiskit's U gate, U(theta, phi, lambda), as used in Takaishi's circuit."""
    c, s = np.cos(theta / 2), np.sin(theta / 2)
    return np.array([[c, -np.exp(1j * lam) * s],
                     [np.exp(1j * phi) * s, np.exp(1j * (phi + lam)) * c]], complex)


def bloch(psi):
    """Bloch vector (x, y, z) of a one-qubit pure state."""
    rho = np.outer(psi, psi.conj())
    return np.real([np.trace(rho @ m) for m in (X, Y, Z)])
