import numpy as np

# FIXME without appending sys.path make it more generic
import sys

sys.path.append("../")

from elastica.wrappers import BaseSystemCollection, Connections, Constraints, Forcing
from elastica.rod.cosserat_rod import CosseratRod
from elastica.boundary_conditions import FreeRod
from elastica.external_forces import GravityForces, UniformTorques
from elastica.interaction import AnistropicFrictionalPlane
from elastica.timestepper.symplectic_steppers import PositionVerlet, PEFRL
from elastica.timestepper import integrate
from FrictionValidationCases.friction_validation_postprocessing import (
    plot_friction_validation,
)


class RollingFrictionInitialVelocitySimulator(
    BaseSystemCollection, Constraints, Forcing
):
    pass


# Options
PLOT_FIGURE = True
SAVE_FIGURE = False
SAVE_RESULTS = False


def simulate_rolling_friction_initial_velocity_with(IFactor=0.0):

    rolling_friction_initial_velocity_sim = RollingFrictionInitialVelocitySimulator()

    # setting up test params
    n_elem = 50
    start = np.zeros((3,))
    direction = np.array([0.0, 0.0, 1.0])
    normal = np.array([0.0, 1.0, 0.0])
    base_length = 1.0
    base_radius = 0.025
    base_area = np.pi * base_radius ** 2
    mass = 1.0
    density = mass / (base_length * base_area)
    nu = 1e-6
    E = 1e9
    # For shear modulus of 2E/3
    poisson_ratio = 0.5

    # Set shear matrix
    shear_matrix = np.repeat(1e4 * np.identity((3))[:, :, np.newaxis], n_elem, axis=2)

    shearable_rod = CosseratRod.straight_rod(
        n_elem,
        start,
        direction,
        normal,
        base_length,
        base_radius,
        density,
        nu,
        E,
        poisson_ratio,
    )

    # TODO: CosseratRod has to be able to take shear matrix as input, we should change it as done below
    shearable_rod.shear_matrix = shear_matrix
    # change the mass moment of inertia matrix and its inverse
    shearable_rod.mass_second_moment_of_inertia *= IFactor
    shearable_rod.inv_mass_second_moment_of_inertia /= IFactor

    # set initial velocity of 1m/s to rod elements in the slip direction
    Vs = 1.0
    shearable_rod.velocity_collection[0, :] += Vs

    rolling_friction_initial_velocity_sim.append(shearable_rod)
    rolling_friction_initial_velocity_sim.constrain(shearable_rod).using(FreeRod)

    # Add gravitational forces
    gravitational_acc = -9.80665
    rolling_friction_initial_velocity_sim.add_forcing_to(shearable_rod).using(
        GravityForces, acc_gravity=np.array([0.0, gravitational_acc, 0.0])
    )

    # Add friction forces
    origin_plane = np.array([0.0, -base_radius, 0.0])
    normal_plane = np.array([0.0, 1.0, 0.0])
    slip_velocity_tol = 1e-6
    static_mu_array = np.array([0.4, 0.4, 0.4])  # [forward, backward, sideways]
    kinetic_mu_array = np.array([0.2, 0.2, 0.2])  # [forward, backward, sideways]

    rolling_friction_initial_velocity_sim.add_forcing_to(shearable_rod).using(
        AnistropicFrictionalPlane,
        k=10.0,
        nu=1e-4,
        plane_origin=origin_plane,
        plane_normal=normal_plane,
        slip_velocity_tol=slip_velocity_tol,
        static_mu_array=static_mu_array,
        kinetic_mu_array=kinetic_mu_array,
    )

    rolling_friction_initial_velocity_sim.finalize()
    timestepper = PositionVerlet()

    final_time = 2.0
    dt = 1e-6
    total_steps = int(final_time / dt)
    print("Total steps", total_steps)
    positions_over_time, directors_over_time, velocities_over_time = integrate(
        timestepper, rolling_friction_initial_velocity_sim, final_time, total_steps
    )

    # compute translational and rotational energy
    translational_energy = shearable_rod.compute_translational_energy()
    rotational_energy = shearable_rod.compute_rotational_energy()

    # compute translational and rotational energy using analytical equations
    analytical_translational_energy = 0.5 * mass * Vs ** 2 / (1.0 + IFactor / 2) ** 2
    analytical_rotational_energy = (
        0.5 * mass * Vs ** 2 * (IFactor / 2.0) / (1.0 + IFactor / 2) ** 2
    )

    return {
        "rod": shearable_rod,
        "position_history": positions_over_time,
        "velocity_history": velocities_over_time,
        "director_history": directors_over_time,
        "sweep": IFactor / 2.0,
        "translational_energy": translational_energy,
        "rotational_energy": rotational_energy,
        "analytical_translational_energy": analytical_translational_energy,
        "analytical_rotational_energy": analytical_rotational_energy,
    }


if __name__ == "__main__":
    import multiprocessing as mp

    IFactor = list([float(x) / 100.0 for x in range(20, 200, 10)])

    with mp.Pool(mp.cpu_count()) as pool:
        results = pool.map(simulate_rolling_friction_initial_velocity_with, IFactor)

    if PLOT_FIGURE:
        filename = "rolling_friction_initial_velocity.png"
        plot_friction_validation(results, SAVE_FIGURE, filename)

    if SAVE_RESULTS:
        import pickle

        filename = "rolling_friction_initial_velocity.dat"
        file = open(filename, "wb")
        pickle.dump([results], file)
        file.close()