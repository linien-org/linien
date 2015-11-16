RED PID
=======

Overview
########

Digital Servo.

Hardware: `RedPitaya <http://redpitaya.com/>`_
Gateware: using `Migen <https://github.com/m-labs/migen>`_,
`Misoc <https://github.com/m-labs/misoc>`_, and some snippets from the
`RedPitaya Verilog <https://github.com/RedPitaya/RedPitaya>`_.
Software: basic CSR-over-SSH `CLI interface <test/csr.py>`_.
Test benches: see e.g. `IIR transfer function <test/iir_transfer.py>`_.

Features
########

See `gateware/chains.py <gateware/chains.py>`_ for the full flow graph. In general there are two "fast" signal chains, roughly from each of the fast analog input to the corresponding analog output, and four "slow" chains from each of the XADC inputs to the DeltaSigma outputs::

  * fast chain
    input: adc -> iir1_a (first order pipelined) -> demod -> iir2i_b (second order iterative)
           -> x: any of the previous
    process: (x or 0) + dx -> limit_a -> iir1_c -> iir2_d -> iir2i_e
           -> y: any of the previous
    output: y + dy + relock + sweep + modulate -> limit_b -> dac
    signal inputs from crossbar: dx, dy, relock_x
    signal outputs to crossbar: x, y
    state outputs to crossbar: x_saturated, x_railed, y_saturated, y_railed, unlocked
    state inputs from crossbar: x_hold, x_clear, y_hold, y_clear, y_relock
    speed: 125 MHz
    signal path width: 25 bit
    coefficient width: 18 bit (except iir2i: 36 bit)
    coefficient denominator: mostly 2 ** 16

  * slow chain
    input: adc -> x
    process: (x or 0) + dx -> limit_x -> iir2i -> limit_y -> y
    output: y -> dac
    signal inputs from crossbar: dx
    signal outputs to crossbar: x, y
    state outputs to crossbar: saturated, railed
    state inputs from crossbar: hold, clear
    speed: 125 MHz * 8/120 = 8 1/3 MHz
    delta-sigma output: 250 MHz
    signal path width: 25 bit
    coefficient width: 18 bit (except iir2i: 36 bit)
    coefficient denominator: mostly 2 ** 16

  * misc sources and sinks:
    signals:
        XORSHIFT pseudo random noise generator (period 2**25)
        two signal generator channels from standard RedPitaya gateware (web interface)
        two oscilloscope channels to standard RedPitaya gateware (web interface)
        force-0 signal
    states:
        8 digital inputs
        8 gitial outputs
        force-1 state

  * crossbar switching matrices:
    state: any logical-or-combination of the 27 input states and one to each of the 26 outputs
    signal: any of the 16 input signals to each of the 12 output signals
    current/max/min signal value monitors: each input, with clear for each signal

* Propagation delay (single IIR) is about 150 ns, thus some 3 MHz loop bandwidth.
* All registers/states/values exposed on the CSR bus (see `test/csrmap.py <test/csrmap.py>`_)

See Also
########

* NIST Ion Storage Digital Servo (open hardware, open software, open gateware, but Verilog)
  https://github.com/nist-ionstorage/digital-servo
* RedPitaya source code: http://redpitaya.com/

