#!/usr/bin/env python3
""" Test scripts for calculus kernels in elastica
"""
# System imports
import numpy as np
import pytest
from numpy.testing import assert_allclose

from elastica._calculus import _trapezoidal, _two_point_difference, _get_zero_array


def test_get_zero_array():
    assert_allclose(_get_zero_array(3, 1), 0.0)
    assert_allclose(_get_zero_array(3, 2), 0.0 * np.random.randn(3, 1))


class Trapezoidal:
    kernel = _trapezoidal

    @staticmethod
    def oned_setup():
        blocksize = 32
        input_vector = np.random.randn(blocksize)

        first_element = 0.5 * input_vector[0]
        last_element = 0.5 * input_vector[-1]
        correct_vector = np.hstack(
            (first_element, 0.5 * (input_vector[1:] + input_vector[:-1]), last_element)
        )

        return input_vector, correct_vector


class Difference:
    kernel = _two_point_difference

    @staticmethod
    def oned_setup():
        blocksize = 32
        input_vector = np.random.randn(blocksize)

        first_element = input_vector[0]
        last_element = -input_vector[-1]
        correct_vector = np.hstack(
            (first_element, (input_vector[1:] - input_vector[:-1]), last_element)
        )

        return input_vector, correct_vector


@pytest.mark.parametrize("Setup", [Trapezoidal, Difference])
@pytest.mark.parametrize("ndim", [1, 2, 3])
def test_two_point_difference_integrity(Setup, ndim):
    input_vector_oned, correct_vector_oned = Setup.oned_setup()
    dim = 3
    test_vector = input_vector = correct_vector = 0.0

    def setup(in_v, in_dim):
        in_v = in_v.reshape(1, -1)
        out_v = np.repeat(in_v, in_dim, axis=0)
        return out_v

    if ndim == 1:
        input_vector = input_vector_oned
        test_vector = Setup.kernel(input_vector)
        correct_vector = correct_vector_oned
    if ndim == 2:
        input_vector = setup(input_vector_oned, dim)
        test_vector = Setup.kernel(input_vector)
        correct_vector = setup(correct_vector_oned, dim)
    if ndim == 3:
        input_vector = setup(input_vector_oned, dim * dim)
        test_vector = Setup.kernel(input_vector)
        correct_vector = setup(correct_vector_oned, dim * dim)
        input_vector = input_vector.reshape(dim, dim, -1)
        test_vector = test_vector.reshape(dim, dim, -1)
        correct_vector = correct_vector.reshape(dim, dim, -1)

    assert test_vector.shape == input_vector.shape[:-1] + (input_vector.shape[-1] + 1,)
    assert_allclose(test_vector, correct_vector)


def test_trapezoidal_correctness():
    r"""
    Tests integral of a function :math:`f : [a,b] \rightarrow \mathbb{R}`,
         :math:`\int_{a}^{b} f \rightarrow \mathbb{R}`
    where f satisfies the conditions f(a) = f(b) = 0.0
    """
    blocksize = 64
    a = 0.0
    b = np.pi
    dh = (b - a) / (blocksize - 1)

    # Should integrate this well, as end
    input_vector = np.sin(np.linspace(a, b, blocksize))
    test_vector = _trapezoidal(input_vector[1:-1]) * dh

    # Sampling for the analytical derivative needs to be done
    # one a grid that lies in between the actual function for
    # second-order accuracy!
    interior_a = a + 0.5 * dh
    interior_b = b - 0.5 * dh
    correct_vector = np.sin(np.linspace(interior_a, interior_b, blocksize - 1)) * dh

    # Pathetic error of 1e-2 :(
    assert_allclose(np.sum(test_vector), 2.0, atol=1e-3)
    assert_allclose(test_vector, correct_vector, atol=1e-4)


def test_two_point_difference_correctness():
    """
    Tests difference of a function f:[a,b]-> R, i.e
        D f[a,b] -> df[a,b]
    where f satisfies the conditions f(a) = f(b) = 0.0
    """
    blocksize = 128
    a = 0.0
    b = np.pi
    dh = (b - a) / (blocksize - 1)

    # Sampling for the analytical derivative needs to be done
    # one a grid that lies in between the actual function for
    # second-order accuracy!
    interior_a = a + 0.5 * dh
    interior_b = b - 0.5 * dh

    # Should integrate this well
    input_vector = np.sin(np.linspace(a, b, blocksize))
    test_vector = _two_point_difference(input_vector[1:-1]) / dh
    correct_vector = np.cos(np.linspace(interior_a, interior_b, blocksize - 1))

    # Pathetic error of 1e-2 :(
    assert_allclose(test_vector, correct_vector, atol=1e-4)
