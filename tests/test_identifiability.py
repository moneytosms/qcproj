from importlib.util import find_spec

import numpy as np
import pytest

from qcvol.quantum import BornCircuit, MemoryCircuit, paper_probability
from qcvol_next.identifiability import effective_parameters

RNG = np.random.default_rng(5)
X4 = RNG.normal(size=(48, 4))
X6 = RNG.normal(size=(48, 6))
needs_jax = pytest.mark.skipif(find_spec("jax") is None, reason="v2 extra not installed")


def test_paper_readout_has_one_inactive_angle():
    r, v = RNG.uniform(-1, 1, 48), RNG.uniform(0, 1, 48)
    report = effective_parameters(lambda p: paper_probability(r, v, p), 3)
    assert (report.nominal, report.effective) == (3, 2)


@pytest.mark.parametrize("layers", [1, 2, 3, 4])
def test_born_circuit_loses_exactly_the_two_terminal_rz(layers):
    model = BornCircuit(layers)
    report = effective_parameters(lambda p: model.probabilities(X4, p), model.n_params)
    assert report.inactive == 2


@pytest.mark.parametrize("layers", [1, 3])
def test_memory_circuit_loses_its_terminal_rz(layers):
    model = MemoryCircuit(layers)
    report = effective_parameters(lambda p: model.predict(X4, p), model.n_params)
    assert report.inactive == 1


def test_rank_counts_unused_and_redundant_parameters():
    assert effective_parameters(lambda p: X4[:, :3] @ p, 3).inactive == 0
    assert effective_parameters(lambda p: X4[:, :2] @ p[:2], 3).inactive == 1
    assert effective_parameters(lambda p: X4[:, 0] * (p[0] + p[1]), 2).inactive == 1


@needs_jax
class TestV2:
    @pytest.mark.parametrize("layers", [1, 3])
    def test_v2_final_layer_rz_weights_are_inactive(self, layers):
        from qcvol_v2 import models as v2

        spec = v2.Spec("quantum", 6, layers=layers)
        probs, _ = v2.build(spec)
        report = effective_parameters(lambda p: np.asarray(probs(p, X6)), spec.n_params)
        assert report.inactive == 2 * 7

    @pytest.mark.parametrize("layers", [1, 3])
    def test_trimmed_v2_is_full_rank(self, layers):
        from qcvol_next import trimmed_v2 as t

        spec = t.TrimmedSpec(6, layers=layers)
        probs, _ = t.build(spec)
        report = effective_parameters(lambda p: np.asarray(probs(p, X6)), spec.n_params)
        assert report.nominal == report.effective == 28 * layers - 14

    def test_trimmed_v2_matches_v2_whatever_the_dropped_weights(self):
        from qcvol_next import trimmed_v2 as t
        from qcvol_v2 import models as v2

        spec = t.TrimmedSpec(6)
        full = RNG.normal(size=spec.full.n_params)
        trimmed, _ = t.build(spec)
        np.testing.assert_allclose(
            np.asarray(trimmed(full[spec.active], X6)),
            v2.reference_probabilities(spec.full, X6, full),
            atol=1e-12,
        )

    def test_trimmed_gradient_matches_finite_difference(self):
        from qcvol_next import trimmed_v2 as t

        spec = t.TrimmedSpec(6, layers=2)
        x, labels = X6[:20], RNG.integers(0, 4, 20)
        p = RNG.normal(size=spec.n_params)
        _, loss = t.build(spec)
        grad = loss(p, x, labels)[1]
        for i in (0, spec.n_params - 1):
            e = np.zeros_like(p)
            e[i] = 1e-6
            fd = (float(loss(p + e, x, labels)[0]) - float(loss(p - e, x, labels)[0])) / 2e-6
            assert abs(fd - grad[i]) < 1e-6

    def test_trimmed_fit_is_a_v2_solution(self):
        from qcvol_next import trimmed_v2 as t
        from qcvol_v2 import models as v2

        spec = t.TrimmedSpec(4, layers=1)
        x, labels = X4[:40], RNG.integers(0, 4, 40)
        best, _ = t.fit(spec, x, labels, seed=0, restarts=2)
        assert spec.n_params == 10 and spec.full.n_params == 20
        _, value_and_grad = v2.build(spec.full)
        value, grad = value_and_grad(t.expand(spec, best["parameters"]), x, labels)
        assert abs(float(value) - best["train_log_loss"]) < 1e-12
        # Zero gradient in every v2 direction: the dropped weights had nothing to add.
        assert np.max(np.abs(np.asarray(grad))) < 1e-4
