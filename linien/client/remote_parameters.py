from typing import Callable
from rpyc import async_
from linien.common import unpack, pack


class RemoteParameters:
    """A class that provides access to a remote `parameters.Parameters` instance.

    It clones the functionality of the remote `Parameters` instance. E.g.:

        # on the remote side
        p = Parameters(...)
        p.my_param.value = 123

        # on the client side
        r = RemoteParameters(...)

        # RemoteParameters allows for accessing the remote value:
        print(r.my_param.value) # outputs 123

        # it's also possible to set the value (this change is automatically
        # propagated to the server)
        r.my_param.value = 123

        # and we can set up a callback function that is called whenever a
        # parameter changes
        def on_change(value):
            # this function is called whenever `my_param` changes on the server.
            # note that this only works if `call_listeners` is called from
            # time to time as this function is responsible for checking for
            # changed parameters.
            print('parameter arrived!', value)
        r.my_param.on_change(on_change)
        while True:
            r.call_listeners()
            sleep(.1)

    The arguments for __init__ are:

        `remote`:    The root of the rpyc connection ot the server
        `uuid`:      A random unique identifier for this client
        `use_cache`: A boolean indicating whether (most) parameters should be
                     cached locally. If this is not enabled, every access of
                     `r.my_param.value` results in a request to the server.
                     If `use_cache` is enabled, a local cache is used instead.
                     For that purpose, a listener is installed such that the
                     server automatically pushes changes to the client and
                     thus updates the cache. No matter how often you access
                     `r.my_param.value`, each parameter value is only transmitted
                     once (after it was changed).
                     Note that calling `call_listeners` is required for this.
    """

    def __init__(self, remote, uuid: str, use_cache: bool):
        self.remote = remote
        self.uuid = uuid
        self._async_listener_queue = None
        self._async_listener_registering = None

        self._listeners_pending_remote_registration = []
        self._listeners = {}

        self._mimic_remote_parameters(use_cache)
        self._attributes_locked = True

        self.call_listeners()

    def __setattr__(self, name, value):
        """In order to set the value of a parameter,

            parameters.my_param.value = 123

        is used. In order to prevent accidentally forgetting the .value part, i.e.

            parameters.my_param = 123

        we raise an error in this case."""
        if (
            hasattr(self, "_attributes_locked")
            and self._attributes_locked
            and not name.startswith("_")
        ):
            raise Exception(
                "Parameters are locked! Did you mean to set the value of this "
                "parameter instead, i.e. parameters.%s.value = %s" % (name, value)
            )
        super().__setattr__(name, value)

    def _mimic_remote_parameters(self, use_cache: bool):
        """For every remote parameter, instanciate a `RemoteParameter` object
        that allows to mimics the functionality of the remote parameter."""
        # when directly iterating over `exposed_init_parameter_sync`, each iteration
        # triggers a request as it is a netref over an iterator
        # --> the `list` call prevents this and improves startup performance
        all_parameters = list(self.remote.exposed_init_parameter_sync(self.uuid))

        for name, param, value, can_be_cached in all_parameters:
            param = RemoteParameter(self, param, name, use_cache and can_be_cached)
            setattr(self, name, param)
            if use_cache and can_be_cached:
                param._update_cache(value)

        self._attributes_locked = True

    def _register_listener(self, param, callback: Callable):
        """Tells the server to notify our client (identified by `self.uuid`)
        when `param` changes. Registers a function `callback` that will be
        called in this case."""
        if param.name not in self._listeners:
            # parameters that use the cache don't have to be registered on remote
            # side because the client automatically listens for changes.
            # This happens using `init_parameter_sync`
            if not param.use_cache:
                self._listeners_pending_remote_registration.append(param.name)

        self._listeners.setdefault(param.name, [])
        self._listeners[param.name].append(callback)

    def call_listeners(self):
        """Ask the server for changed parameters and call the respective
        callback functions. This call takes place asynchronously, i.e. the first
        run of `call_listeners` just issues the call but does not wait for it
        in order not to block the GUI. The following calls check whether a
        result has arrived (also not blocking GUI).

        In Linien GUI client, this function is called periodically.
        If you use the python client and want to use callbacks for changed
        parameters you have to call this method manually from time to time."""

        def _get_listener_queue_async():
            """Issues an asynchronous call (that does not block the GUI) to the
            server in order to retrieve a batch of changed parameters."""
            self._async_listener_queue = async_(self.remote.get_listener_queue)(
                self.uuid
            )

        def _register_listeners_async():
            """Issues an asynchronous call to the server containing all the
            parameters that this client wants to be notified of in case of a
            changed value."""
            pending = self._listeners_pending_remote_registration
            if pending:
                # this copies the list before clearing it below. Otherwise
                # we just transmit an epmty list in the async call
                pending = pending[:]
                self._async_listener_registering = async_(
                    self.remote.exposed_register_remote_listeners
                )(self.uuid, pending)
                self._listeners_pending_remote_registration.clear()

        if self._async_listener_queue is None:
            # this means that the async call was not started yet --> start it
            # the next call to `call_listeners` will then check whether the
            # the result is ready.
            _get_listener_queue_async()

        if self._async_listener_registering is None:
            _register_listeners_async()

        if self._async_listener_queue is not None and self._async_listener_queue.ready:
            # we have a result
            queue = unpack(self._async_listener_queue.value)

            # now that we have our result, we can start the next call
            _get_listener_queue_async()

            # before calling listeners, we update cache for all received parameters
            # at once
            for param_name, value in queue:
                param = getattr(self, param_name)
                if param.use_cache:
                    param._update_cache(value)

            # iterate over all canged parameters and call the respective
            # callback functions
            for param_name, value in queue:
                if param_name in self._listeners:
                    for listener in self._listeners[param_name]:
                        listener(value)

        if (
            self._async_listener_registering is not None
            and self._async_listener_registering.ready
        ):
            # registration of listeners was successful on the remote side
            # now we can clear the async call object such that a new one may
            # be issued (if required)
            self._async_listener_registering = None

    def _get_param(self, param_name):
        return unpack(self.remote.exposed_get_param(param_name))

    def _set_param(self, param_name, value):
        return self.remote.exposed_set_param(param_name, pack(value))


class RemoteParameter:
    """A helper class for `RemoteParameters`, representing a single remote
    parameter."""

    def __init__(
        self, parent: RemoteParameters, remote_param, name: str, use_cache: bool
    ):
        self._remote_param = remote_param
        self.name = name
        self.parent = parent
        self.use_cache = use_cache

    @property
    def value(self):
        """Return the locally cached value (if it exists). Otherwise ask the
        server."""
        if hasattr(self, "_cached_value"):
            return self._cached_value
        return self.parent._get_param(self.name)

    @value.setter
    def value(self, value):
        """Notify the server of the new value"""
        return self.parent._set_param(self.name, value)

    def on_change(self, callback_on_change, call_listener_with_first_value=True):
        """Tells the server that `callback_on_change` should be called whenever
        the parameter changes."""
        self.parent._register_listener(self, callback_on_change)

        if call_listener_with_first_value:
            # call the callback with the initial value
            callback_on_change(self.value)

    def reset(self):
        """Reset the value to its initial value"""
        self._remote_param.reset()

    def _update_cache(self, value):
        self._cached_value = value
