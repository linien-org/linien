# Copyright 2018-2022 Benjamin Wiegand <benjamin.wiegand@physik.hu-berlin.de>
# Copyright 2021-2022 Bastian Leykauf <leykauf@physik.hu-berlin.de>
#
# This file is part of Linien and based on redpid.
#
# Linien is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Linien is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Linien.  If not, see <http://www.gnu.org/licenses/>.

"""Module providing the Optimizer interface class."""

from typing import List, NewType

Params = NewType("Params", List[float])
"""A type alias for actual optmizer params. """


class Optimizer:
    """Interface for the "Optimizer" type classes."""

    def __init__(self):
        self._generation = 0
        """Generation counter."""

        self._upper_limits = []
        """Upper parameter limit for each dimension."""

        self._lower_limits = []
        """Lower parameter limit for each dimension."""

        self._boundary_conditions = []
        """Complex boundary conditions list"""

    def request_parameter_set(self):
        """Ask the engine for a new param set to try out."""

        raise NotImplementedError("request_parameter_set is not implemented.")
        return []

    def insert_fitness_value(self, fitness, set):
        """Tell the engine about our experiment result."""
        raise NotImplementedError("insert_fitness_value not implemented")

    def request_results(self):
        """Return a list of promising results."""
        raise NotImplementedError("request_results not implemented")
        return []

    @property
    def generation(self):
        return self._generation

    def _truncate_parameters(self, params):
        """
        Make sure the passed list of parameters is within [min, max] if available,
        respectively.
        """

        if self._lower_limits != []:
            params = [
                max(low_lim, par) for low_lim, par in zip(self._lower_limits, params)
            ]

        if self._upper_limits != []:
            params = [
                min(low_lim, par) for low_lim, par in zip(self._upper_limits, params)
            ]

        if self._boundary_conditions != []:
            for condition in self._boundary_conditions:
                params = condition.check_and_correct(params)

        return params


class Individual:
    """A parameter set of an optimization algorithm."""

    def __init__(self, param_set, fitness):
        self.param_set = param_set
        self.fitness = fitness
        self.generation = 0

    def __lt__(self, other):
        return self.fitness < other.fitness

    def __gt__(self, other):
        return self.fitness > other.fitness

    def __copy__(self):
        ind = Individual(self.param_set.copy(), self.fitness)
        ind.generation = self.generation
        return ind
