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

import atexit
import pickle
from time import time

import linien_server

PARAMETER_STORE_FN = "/linien_parameters.pickle"


class ParameterStore:
    """This class installs an `atexit` listener that persists parameters to disk
    when the server shuts down. Once it restarts the parameters are restored."""

    def __init__(self, parameters):
        self.parameters = parameters
        self.restore_parameters()
        self.setup_listener()

    def setup_listener(self):
        """Listen for shutdown"""
        atexit.register(self.save_parameters)

    def restore_parameters(self):
        """When the server starts, this method restores previously saved
        parameters (if any)."""
        try:
            with open(PARAMETER_STORE_FN, "rb") as f:
                data = pickle.load(f)
        except (FileNotFoundError, pickle.UnpicklingError, EOFError):
            return

        print("restore parameters")

        for param_name, value in data["parameters"].items():
            try:
                getattr(self.parameters, param_name).value = value
            except AttributeError:
                # ignore parameters that don't exist (anymore)
                continue

    def save_parameters(self):
        """Gather all parameters and store them on disk."""
        print("save parameters")
        parameters = {}

        for param_name in self.parameters._restorable_parameters:
            param = getattr(self.parameters, param_name)
            parameters[param_name] = param.value

        try:
            with open(PARAMETER_STORE_FN, "wb") as f:
                pickle.dump(
                    {
                        "parameters": parameters,
                        "time": time(),
                        "version": linien_server.__version__,
                    },
                    f,
                )
        except PermissionError:
            # this may happen if the server doesn't run on RedPitaya but on the
            # developer's machine. As it is not a critical problem, just print
            # the exception and ignore it
            from traceback import print_exc

            print_exc()
