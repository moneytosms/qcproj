import numpy as np
import pytest

from qcvol.quantum import (
    CNOT,
    BornCircuit,
    encoded_state,
    paper_probability,
    paper_twin,
    ry,
    rz,
    u3,
    verify_paper,
)


@pytest.mark.parametrize("angle", [0, 0.1, -2.8, np.pi])
def test_gates_are_unitary(angle):
    for gate in (ry(angle), rz(angle), u3(angle, 0.7, -1.1), CNOT):
        np.testing.assert_allclose(gate.conj().T @ gate, np.eye(len(gate)), atol=1e-14)


def test_paper_twin_and_dead_phi():
    rng = np.random.default_rng(43)
    r, v = rng.uniform(-1, 1, 100), rng.uniform(0, 1, 100)
    for _ in range(8):
        p = rng.normal(size=3)
        expected = paper_twin(r, v, p)
        np.testing.assert_allclose(paper_probability(r, v, p), expected, atol=1e-14)
        p[1] += 10
        np.testing.assert_allclose(paper_probability(r, v, p), expected, atol=1e-14)
    assert verify_paper()["twin_max_error"] < 1e-14


def reference_born(x, parameters, layers):
    state = np.array([1, 0, 0, 0], complex)
    for w in parameters.reshape(layers, 8):
        q0 = rz(w[1] * x[1]) @ ry(w[0] * x[0])
        q1 = rz(w[3] * x[3]) @ ry(w[2] * x[2])
        state = np.kron(q0, q1) @ state
        state = CNOT @ np.kron(rz(w[5]) @ ry(w[4]), rz(w[7]) @ ry(w[6])) @ state
    return np.abs(state) ** 2


@pytest.mark.parametrize("layers", [1, 2, 3, 4])
def test_born_matches_independent_matrix_circuit(layers):
    rng = np.random.default_rng(53)
    x, parameters = rng.normal(size=(9, 4)), rng.normal(size=layers * 8)
    model = BornCircuit(layers)
    expected = np.array([reference_born(row, parameters, layers) for row in x])
    actual = model.probabilities(x, parameters)
    np.testing.assert_allclose(actual, expected, atol=1e-14)
    np.testing.assert_allclose(actual.sum(axis=1), 1, atol=1e-14)
    assert np.min(actual) >= 0


def test_terminal_phase_angles_are_unobservable_in_born_circuit():
    rng = np.random.default_rng(71)
    x, p = rng.normal(size=(20, 4)), rng.normal(size=24)
    changed = p.copy()
    changed[-3] += 2.3  # final layer RZ on qubit 0
    changed[-1] -= 1.2  # final layer RZ on qubit 1
    np.testing.assert_allclose(
        BornCircuit().probabilities(x, p), BornCircuit().probabilities(x, changed), atol=1e-14
    )


def test_invalid_paper_encoding_is_rejected():
    with pytest.raises(ValueError, match="requires"):
        encoded_state([1.01], [0.2])
    with pytest.raises(ValueError, match="requires"):
        encoded_state([0.1], [-0.01])
