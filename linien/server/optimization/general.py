"""Module providing the Optimizer interface class."""

from typing import List, NewType, Optional

Params = NewType('Params', List[float])
"""A type alias for actual optmizer params. """

class Optimizer:
    """Interface for the "Optimizer" type classes."""

    def __init__(self) -> None:
        self._generation: int = 0
        """Generation counter."""

        self._upper_limits: List[Optional[float]] = []
        """Upper parameter limit for each dimension."""

        self._lower_limits: List[Optional[float]] = []
        """Lower parameter limit for each dimension."""

        self._boundary_conditions = []
        """Complex boundary conditions list"""

    def request_parameter_set(self) -> Params:
        """Ask the engine for a new param set to try out."""

        raise NotImplementedError("request_parameter_set is not implemented.")
        return []

    def insert_fitness_value(self, fitness: float, set: Params) -> None:
        """Tell the engine about our experiment result."""
        raise NotImplementedError("insert_fitness_value not implemented")

    def request_results(self) -> List[Params]:
        """Return a list of promising results."""
        raise NotImplementedError("request_results not implemented")
        return []

    @property
    def generation(self) -> int:
        return self._generation

    def _truncate_parameters(self, params: Params) -> Params:
        """Make sure the passed list of parameters is within [min, max] if available respectively."""

        if self._lower_limits != []:
            params = [max(l, r) for l, r in zip(self._lower_limits, params)]

        if self._upper_limits != []:
            params = [min(l, r) for l, r in zip(self._upper_limits, params)]

        if self._boundary_conditions != []:
            for condition in self._boundary_conditions:
                params = condition.check_and_correct(params)

        return params


class Individual:
    """A parameter set of an optimization algorithm."""

    def __init__(self, param_set: Params, fitness: float):
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
