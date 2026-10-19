"""Shared scores: forecast quality and realism of generated histories."""
import numpy as np


def acf(x, lag):
    x = np.asarray(x, float)
    return np.corrcoef(x[:-lag], x[lag:])[0, 1]


def realism_moments(logrv, lags=(1, 7, 30)):
    """Autocorrelation of log RV at the given lags, plus the spread of daily changes (vol-of-vol)."""
    return np.array([acf(logrv, k) for k in lags] + [np.diff(logrv).std()])


def moment_distance(gen, real, scale=(0.1, 0.1, 0.1, 0.3)):
    return float(np.sum(((np.asarray(gen) - np.asarray(real)) / np.asarray(scale)) ** 2))


def hill_tail_index(x, frac=0.05):
    """Hill estimator of the tail index of |x| using the top `frac` of observations."""
    a = np.sort(np.abs(np.asarray(x, float)))[::-1]
    k = max(int(frac * len(a)), 10)
    return 1.0 / np.mean(np.log(a[:k] / a[k]))


def log_loss(P, labels):
    return float(-np.mean(np.log(P[np.arange(len(labels)), labels] + 1e-12)))


def rps(P, labels):
    """Ranked probability score for ordered levels (lower is better)."""
    K = P.shape[1]
    c = np.cumsum(P, 1)[:, :-1]
    o = (np.arange(K - 1)[None, :] >= np.asarray(labels)[:, None]).astype(float)
    return float(np.mean(np.sum((c - o) ** 2, 1)))


def mfdfa(x, qs=np.arange(-5, 5.5, 0.5), scales=None, order=3):
    """Multifractal detrended fluctuation analysis (Kantelhardt et al. 2002), as in the paper.

    Cubic detrending, segments taken from both ends. Returns (qs, h(q)).
    """
    x = np.asarray(x, float)
    N = len(x)
    if scales is None:
        scales = np.unique(np.logspace(np.log10(10), np.log10(N // 5), 15).astype(int))
    y = np.cumsum(x - x.mean())
    logF = np.empty((len(qs), len(scales)))
    for j, s in enumerate(scales):
        ns = N // s
        segs = [y[v * s:(v + 1) * s] for v in range(ns)] + [y[N - (v + 1) * s:N - v * s] for v in range(ns)]
        i = np.arange(s)
        f2 = np.array([np.mean((seg - np.polyval(np.polyfit(i, seg, order), i)) ** 2) for seg in segs])
        f2 = np.maximum(f2, 1e-300)
        for k, q in enumerate(qs):
            if abs(q) < 1e-12:
                logF[k, j] = 0.5 * np.mean(np.log(f2))
            else:
                logF[k, j] = np.log(np.mean(f2 ** (q / 2))) / q
    ls = np.log(scales)
    h = np.array([np.polyfit(ls, logF[k], 1)[0] for k in range(len(qs))])
    return qs, h


def hurst2(x, **kw):
    qs, h = mfdfa(x, qs=np.array([2.0]), **kw)
    return float(h[0])


def mf_width(x, **kw):
    """Spread of h(q) between q = -5 and q = 5: zero for a monofractal series."""
    qs, h = mfdfa(x, qs=np.array([-5.0, 5.0]), **kw)
    return float(h[0] - h[1])
