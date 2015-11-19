v 20150930 2
C 24400 30900 0 0 0 title-A2.sym
C 27800 44100 1 0 0 BNC-1.sym
{
T 28150 44750 5 10 0 0 0 0 1
device=BNC
T 27800 44100 5 10 0 0 0 0 1
documentation=http://www.molex.com/pdm_docs/sd/732512201_sd.pdf
T 27900 44800 5 10 1 1 0 0 1
refdes=J200
T 26300 44500 5 10 1 1 0 0 1
footprint=sma_panel_angle
T 27000 44300 5 10 1 1 0 0 1
value=fast_a_in
}
C 43200 43700 1 0 1 BNC-1.sym
{
T 42850 44350 5 10 0 0 0 6 1
device=BNC
T 43200 43700 5 10 0 0 0 6 1
documentation=http://www.molex.com/pdm_docs/sd/732512201_sd.pdf
T 43100 44400 5 10 1 1 0 6 1
refdes=J206
T 44700 44100 5 10 1 1 0 6 1
footprint=sma_panel_angle
T 44100 43800 5 10 1 1 0 6 1
value=fast_a_out
}
C 33600 43700 1 0 1 BNC-1.sym
{
T 33250 44350 5 10 0 0 0 6 1
device=BNC
T 33600 43700 5 10 0 0 0 6 1
documentation=http://www.molex.com/pdm_docs/sd/732512201_sd.pdf
T 33500 44400 5 10 1 1 0 6 1
refdes=J202
T 34500 44000 5 10 1 1 0 6 1
footprint=sma_vert
T 34300 43700 5 10 1 1 0 6 1
value=rp_in1
}
C 36800 44100 1 0 0 BNC-1.sym
{
T 37150 44750 5 10 0 0 0 0 1
device=BNC
T 36800 44100 5 10 0 0 0 0 1
documentation=http://www.molex.com/pdm_docs/sd/732512201_sd.pdf
T 36900 44800 5 10 1 1 0 0 1
refdes=J203
T 36000 44400 5 10 1 1 0 0 1
footprint=sma_vert
T 36000 44200 5 10 1 1 0 0 1
value=rp_out1
}
C 29000 43700 1 90 0 resistor-1.sym
{
T 28600 44000 5 10 0 0 90 0 1
device=RESISTOR
T 29000 43700 5 10 0 1 0 0 1
footprint=0603
T 29000 44200 5 10 1 1 0 0 1
refdes=R200
T 29000 44000 5 10 1 1 0 0 1
value=100k
}
C 29600 43100 1 0 0 ad825x.sym
{
T 30250 44700 5 10 0 0 0 0 1
device=INAMP
T 30300 44300 5 10 1 1 0 6 1
refdes=U200
T 30250 45300 5 10 0 0 0 0 1
footprint=MSOP10
T 30250 44900 5 10 0 0 0 0 1
symversion=1.0
T 29900 44100 5 10 1 1 0 0 1
value=AD8253
T 29600 43100 5 10 0 0 0 0 1
documentation=http://www.analog.com/media/en/technical-documentation/data-sheets/AD8253.pdf
}
C 29000 42800 1 90 0 resistor-1.sym
{
T 28600 43100 5 10 0 0 90 0 1
device=RESISTOR
T 29000 42800 5 10 0 1 0 0 1
footprint=0603
T 29000 43300 5 10 1 1 0 0 1
refdes=R201
T 29000 43100 5 10 1 1 0 0 1
value=1M
}
C 29100 42800 1 180 0 generic-power.sym
{
T 28900 42550 5 10 1 1 180 3 1
net=AGND:1
}
C 33700 42400 1 180 0 generic-power.sym
{
T 33500 42150 5 10 1 1 180 3 1
net=AGND:1
}
C 43300 42400 1 180 0 generic-power.sym
{
T 43100 42150 5 10 1 1 180 3 1
net=AGND:1
}
C 30400 42300 1 90 0 capacitor-1.sym
{
T 29700 42500 5 10 0 0 90 0 1
device=CAPACITOR
T 29700 42500 5 10 1 1 0 0 1
refdes=C201
T 29500 42500 5 10 0 0 90 0 1
symversion=0.1
T 30400 42300 5 10 0 1 0 0 1
footprint=0603
T 29700 42300 5 10 1 1 0 0 1
value=100n
}
C 30400 42300 1 180 0 generic-power.sym
{
T 30200 42050 5 10 1 1 180 3 1
net=AGND:1
}
C 30000 43200 1 180 0 generic-power.sym
{
T 29800 42950 5 10 1 1 180 3 1
net=-15V:1
}
C 30800 43300 1 180 0 generic-power.sym
{
T 30600 43050 5 10 1 1 180 3 1
net=DGND:1
}
N 30600 43300 30600 43600 4
N 31000 43300 31000 43800 4
N 30200 43200 30200 43400 4
N 29800 43200 30200 43200 4
C 29800 46200 1 270 0 capacitor-1.sym
{
T 30500 46000 5 10 0 0 270 0 1
device=CAPACITOR
T 30700 46000 5 10 0 0 270 0 1
symversion=0.1
T 29800 46200 5 10 0 1 180 0 1
footprint=0603
T 29500 46000 5 10 1 1 0 0 1
refdes=C200
T 29500 45800 5 10 1 1 0 0 1
value=100n
}
C 29800 46200 1 0 0 generic-power.sym
{
T 30000 46450 5 10 1 1 0 3 1
net=AGND:1
}
C 29400 45300 1 0 0 generic-power.sym
{
T 29600 45550 5 10 1 1 0 3 1
net=+15V:1
}
N 30000 45300 30000 45100 4
N 29600 45300 30000 45300 4
C 30300 46300 1 270 0 input-2.sym
{
T 30300 46500 5 10 1 1 270 0 1
net=INA_A0:1
T 31000 45700 5 10 0 0 270 0 1
device=none
T 30400 45800 5 10 0 1 270 7 1
value=INPUT
}
C 30500 46200 1 270 0 input-2.sym
{
T 30500 46400 5 10 1 1 270 0 1
net=INA_A1:1
T 31200 45600 5 10 0 0 270 0 1
device=none
T 30600 45700 5 10 0 1 270 7 1
value=INPUT
}
C 30700 46100 1 270 0 input-2.sym
{
T 30800 46800 5 10 1 1 270 0 1
net=INA_WR_FAI:1
T 31400 45500 5 10 0 0 270 0 1
device=none
T 30800 45600 5 10 0 1 270 7 1
value=INPUT
}
N 27900 43700 29600 43700 4
N 28300 44600 29600 44600 4
C 32700 44300 1 180 0 resistor-1.sym
{
T 32400 43900 5 10 0 0 180 0 1
device=RESISTOR
T 32700 44300 5 10 0 1 90 0 1
footprint=0603
T 31900 44400 5 10 1 1 0 0 1
refdes=R202
T 32300 44400 5 10 1 1 0 0 1
value=9.01k*
}
N 31600 44200 31800 44200 4
C 32800 43300 1 90 0 resistor-1.sym
{
T 32400 43600 5 10 0 0 90 0 1
device=RESISTOR
T 32800 43300 5 10 0 1 0 0 1
footprint=0603
T 32800 43800 5 10 1 1 0 0 1
refdes=R203
T 32800 43600 5 10 1 1 0 0 1
value=1k*
}
N 32700 44200 33100 44200 4
C 33400 42300 1 0 0 jumper-1.sym
{
T 33700 42800 5 8 0 0 0 0 1
device=JUMPER
T 33700 43000 5 10 1 1 0 0 1
refdes=B200
T 33700 42700 5 10 0 1 0 0 1
footprint=solderbridge
}
N 31000 43300 33500 43300 4
N 33500 43300 33500 43700 4
N 27900 44100 27900 43700 4
C 38100 43700 1 90 0 resistor-1.sym
{
T 37700 44000 5 10 0 0 90 0 1
device=RESISTOR
T 38100 43700 5 10 0 1 0 0 1
footprint=0603
T 38100 44200 5 10 1 1 0 0 1
refdes=R207
T 38100 44000 5 10 1 1 0 0 1
value=49.9*
}
C 38700 43100 1 0 0 ad825x.sym
{
T 39350 44700 5 10 0 0 0 0 1
device=INAMP
T 39350 45300 5 10 0 0 0 0 1
footprint=MSOP10
T 39350 44900 5 10 0 0 0 0 1
symversion=1.0
T 39400 44300 5 10 1 1 0 6 1
refdes=U202
T 39000 44100 5 10 1 1 0 0 1
value=AD8250
T 38700 43100 5 10 0 0 0 0 1
documentation=http://www.analog.com/media/en/technical-documentation/data-sheets/AD8250.pdf
}
C 38100 42800 1 90 0 resistor-1.sym
{
T 37700 43100 5 10 0 0 90 0 1
device=RESISTOR
T 38100 42800 5 10 0 1 0 0 1
footprint=0603
T 38100 43300 5 10 1 1 0 0 1
refdes=R208
T 38100 43100 5 10 1 1 0 0 1
value=1M
}
C 38200 42800 1 180 0 generic-power.sym
{
T 38000 42550 5 10 1 1 180 3 1
net=AGND:1
}
C 39500 42300 1 90 0 capacitor-1.sym
{
T 38800 42500 5 10 0 0 90 0 1
device=CAPACITOR
T 38600 42500 5 10 0 0 90 0 1
symversion=0.1
T 39500 42300 5 10 0 1 0 0 1
footprint=0603
T 38800 42500 5 10 1 1 0 0 1
refdes=C205
T 38800 42300 5 10 1 1 0 0 1
value=100n
}
C 39500 42300 1 180 0 generic-power.sym
{
T 39300 42050 5 10 1 1 180 3 1
net=AGND:1
}
C 39100 43200 1 180 0 generic-power.sym
{
T 38900 42950 5 10 1 1 180 3 1
net=-15V:1
}
C 39900 43300 1 180 0 generic-power.sym
{
T 39700 43050 5 10 1 1 180 3 1
net=DGND:1
}
N 39700 43300 39700 43600 4
N 40100 43300 40100 43800 4
N 39300 43200 39300 43400 4
N 38900 43200 39300 43200 4
C 38900 46200 1 270 0 capacitor-1.sym
{
T 39600 46000 5 10 0 0 270 0 1
device=CAPACITOR
T 39800 46000 5 10 0 0 270 0 1
symversion=0.1
T 38900 46200 5 10 0 1 180 0 1
footprint=0603
T 38600 46000 5 10 1 1 0 0 1
refdes=C203
T 38600 45800 5 10 1 1 0 0 1
value=100n
}
C 38900 46200 1 0 0 generic-power.sym
{
T 39100 46450 5 10 1 1 0 3 1
net=AGND:1
}
C 38500 45300 1 0 0 generic-power.sym
{
T 38700 45550 5 10 1 1 0 3 1
net=+15V:1
}
N 39100 45300 39100 45100 4
N 38700 45300 39100 45300 4
C 39400 46300 1 270 0 input-2.sym
{
T 40100 45700 5 10 0 0 270 0 1
device=none
T 39500 45800 5 10 0 1 270 7 1
value=INPUT
T 39400 46500 5 10 1 1 270 0 1
net=INA_A0:1
}
C 39600 46200 1 270 0 input-2.sym
{
T 40300 45600 5 10 0 0 270 0 1
device=none
T 39700 45700 5 10 0 1 270 7 1
value=INPUT
T 39600 46400 5 10 1 1 270 0 1
net=INA_A1:1
}
C 39800 46100 1 270 0 input-2.sym
{
T 40500 45500 5 10 0 0 270 0 1
device=none
T 39900 45600 5 10 0 1 270 7 1
value=INPUT
T 39900 46800 5 10 1 1 270 0 1
net=INA_WR_FAO:1
}
C 41800 44300 1 180 0 resistor-1.sym
{
T 41500 43900 5 10 0 0 180 0 1
device=RESISTOR
T 41800 44300 5 10 0 1 90 0 1
footprint=0603
T 41100 44400 5 10 1 1 0 0 1
refdes=R210
T 41500 44400 5 10 1 1 0 0 1
value=49.9*
}
N 40700 44200 40900 44200 4
N 41800 44200 42700 44200 4
N 36900 44100 36900 43700 4
N 36900 43700 38700 43700 4
N 37300 44600 38700 44600 4
C 42400 43300 1 90 0 capacitor-1.sym
{
T 41700 43500 5 10 0 0 90 0 1
device=CAPACITOR
T 41500 43500 5 10 0 0 90 0 1
symversion=0.1
T 42400 43300 5 10 0 1 0 0 1
footprint=0603
T 41700 43500 5 10 1 1 0 0 1
refdes=C206
T 41700 43300 5 10 1 1 0 0 1
value=300p
}
C 43000 42300 1 0 0 jumper-1.sym
{
T 43300 42800 5 8 0 0 0 0 1
device=JUMPER
T 43300 43000 5 10 1 1 0 0 1
refdes=B202
T 43300 42700 5 10 0 1 0 0 1
footprint=solderbridge
}
N 43100 43300 43100 43700 4
N 40100 43300 43100 43300 4
C 27600 38000 1 0 0 BNC-1.sym
{
T 27950 38650 5 10 0 0 0 0 1
device=BNC
T 27600 38000 5 10 0 0 0 0 1
documentation=http://www.molex.com/pdm_docs/sd/732512201_sd.pdf
T 27700 38700 5 10 1 1 0 0 1
refdes=J201
T 26100 38400 5 10 1 1 0 0 1
footprint=sma_panel_angle
T 26800 38200 5 10 1 1 0 0 1
value=fast_b_in
}
C 43000 37600 1 0 1 BNC-1.sym
{
T 42650 38250 5 10 0 0 0 6 1
device=BNC
T 43000 37600 5 10 0 0 0 6 1
documentation=http://www.molex.com/pdm_docs/sd/732512201_sd.pdf
T 42900 38300 5 10 1 1 0 6 1
refdes=J207
T 44500 38000 5 10 1 1 0 6 1
footprint=sma_panel_angle
T 43900 37700 5 10 1 1 0 6 1
value=fast_b_out
}
C 33400 37600 1 0 1 BNC-1.sym
{
T 33050 38250 5 10 0 0 0 6 1
device=BNC
T 33400 37600 5 10 0 0 0 6 1
documentation=http://www.molex.com/pdm_docs/sd/732512201_sd.pdf
T 33300 38300 5 10 1 1 0 6 1
refdes=J204
T 34300 37900 5 10 1 1 0 6 1
footprint=sma_vert
T 34100 37600 5 10 1 1 0 6 1
value=rp_in2
}
C 36600 38000 1 0 0 BNC-1.sym
{
T 36950 38650 5 10 0 0 0 0 1
device=BNC
T 36600 38000 5 10 0 0 0 0 1
documentation=http://www.molex.com/pdm_docs/sd/732512201_sd.pdf
T 36700 38700 5 10 1 1 0 0 1
refdes=J205
T 35800 38300 5 10 1 1 0 0 1
footprint=sma_vert
T 35800 38100 5 10 1 1 0 0 1
value=rp_out2
}
C 28800 37600 1 90 0 resistor-1.sym
{
T 28400 37900 5 10 0 0 90 0 1
device=RESISTOR
T 28800 37600 5 10 0 1 0 0 1
footprint=0603
T 28800 38100 5 10 1 1 0 0 1
refdes=R204
T 28800 37900 5 10 1 1 0 0 1
value=100k
}
C 29400 37000 1 0 0 ad825x.sym
{
T 30050 38600 5 10 0 0 0 0 1
device=INAMP
T 30050 39200 5 10 0 0 0 0 1
footprint=MSOP10
T 30050 38800 5 10 0 0 0 0 1
symversion=1.0
T 29400 37000 5 10 0 0 0 0 1
documentation=http://www.analog.com/media/en/technical-documentation/data-sheets/AD8253.pdf
T 30100 38200 5 10 1 1 0 6 1
refdes=U201
T 29700 38000 5 10 1 1 0 0 1
value=AD8253
}
C 28800 36700 1 90 0 resistor-1.sym
{
T 28400 37000 5 10 0 0 90 0 1
device=RESISTOR
T 28800 36700 5 10 0 1 0 0 1
footprint=0603
T 28800 37200 5 10 1 1 0 0 1
refdes=R205
T 28800 37000 5 10 1 1 0 0 1
value=1M
}
C 28900 36700 1 180 0 generic-power.sym
{
T 28700 36450 5 10 1 1 180 3 1
net=AGND:1
}
C 33500 36300 1 180 0 generic-power.sym
{
T 33300 36050 5 10 1 1 180 3 1
net=AGND:1
}
C 43100 36300 1 180 0 generic-power.sym
{
T 42900 36050 5 10 1 1 180 3 1
net=AGND:1
}
C 30200 36200 1 90 0 capacitor-1.sym
{
T 29500 36400 5 10 0 0 90 0 1
device=CAPACITOR
T 29300 36400 5 10 0 0 90 0 1
symversion=0.1
T 30200 36200 5 10 0 1 0 0 1
footprint=0603
T 29500 36400 5 10 1 1 0 0 1
refdes=C204
T 29500 36200 5 10 1 1 0 0 1
value=100n
}
C 30200 36200 1 180 0 generic-power.sym
{
T 30000 35950 5 10 1 1 180 3 1
net=AGND:1
}
C 29800 37100 1 180 0 generic-power.sym
{
T 29600 36850 5 10 1 1 180 3 1
net=-15V:1
}
C 30600 37200 1 180 0 generic-power.sym
{
T 30400 36950 5 10 1 1 180 3 1
net=DGND:1
}
N 30400 37200 30400 37500 4
N 30800 37200 30800 37700 4
N 30000 37100 30000 37300 4
N 29600 37100 30000 37100 4
C 29600 40100 1 270 0 capacitor-1.sym
{
T 30300 39900 5 10 0 0 270 0 1
device=CAPACITOR
T 30500 39900 5 10 0 0 270 0 1
symversion=0.1
T 29600 40100 5 10 0 1 180 0 1
footprint=0603
T 29300 39900 5 10 1 1 0 0 1
refdes=C202
T 29300 39700 5 10 1 1 0 0 1
value=100n
}
C 29600 40100 1 0 0 generic-power.sym
{
T 29800 40350 5 10 1 1 0 3 1
net=AGND:1
}
C 29200 39200 1 0 0 generic-power.sym
{
T 29400 39450 5 10 1 1 0 3 1
net=+15V:1
}
N 29800 39200 29800 39000 4
N 29400 39200 29800 39200 4
C 30100 40200 1 270 0 input-2.sym
{
T 30800 39600 5 10 0 0 270 0 1
device=none
T 30200 39700 5 10 0 1 270 7 1
value=INPUT
T 30100 40400 5 10 1 1 270 0 1
net=INA_A0:1
}
C 30300 40100 1 270 0 input-2.sym
{
T 31000 39500 5 10 0 0 270 0 1
device=none
T 30400 39600 5 10 0 1 270 7 1
value=INPUT
T 30300 40300 5 10 1 1 270 0 1
net=INA_A1:1
}
C 30500 40000 1 270 0 input-2.sym
{
T 31200 39400 5 10 0 0 270 0 1
device=none
T 30600 39500 5 10 0 1 270 7 1
value=INPUT
T 30600 40700 5 10 1 1 270 0 1
net=INA_WR_FBI:1
}
N 27700 37600 29400 37600 4
N 28100 38500 29400 38500 4
C 32500 38200 1 180 0 resistor-1.sym
{
T 32200 37800 5 10 0 0 180 0 1
device=RESISTOR
T 32500 38200 5 10 0 1 90 0 1
footprint=0603
T 31700 38300 5 10 1 1 0 0 1
refdes=R206
T 32100 38300 5 10 1 1 0 0 1
value=9.01k*
}
N 31400 38100 31600 38100 4
C 32600 37200 1 90 0 resistor-1.sym
{
T 32200 37500 5 10 0 0 90 0 1
device=RESISTOR
T 32600 37200 5 10 0 1 0 0 1
footprint=0603
T 32600 37700 5 10 1 1 0 0 1
refdes=R209
T 32600 37500 5 10 1 1 0 0 1
value=1k*
}
N 32500 38100 32900 38100 4
C 33200 36200 1 0 0 jumper-1.sym
{
T 33500 36700 5 8 0 0 0 0 1
device=JUMPER
T 33500 36600 5 10 0 1 0 0 1
footprint=solderbridge
T 33500 36900 5 10 1 1 0 0 1
refdes=B201
}
N 30800 37200 33300 37200 4
N 33300 37200 33300 37600 4
N 27700 38000 27700 37600 4
C 37900 37600 1 90 0 resistor-1.sym
{
T 37500 37900 5 10 0 0 90 0 1
device=RESISTOR
T 37900 37600 5 10 0 1 0 0 1
footprint=0603
T 37900 38100 5 10 1 1 0 0 1
refdes=R211
T 37900 37900 5 10 1 1 0 0 1
value=49.9*
}
C 38500 37000 1 0 0 ad825x.sym
{
T 39150 38600 5 10 0 0 0 0 1
device=INAMP
T 39150 39200 5 10 0 0 0 0 1
footprint=MSOP10
T 39150 38800 5 10 0 0 0 0 1
symversion=1.0
T 38500 37000 5 10 0 0 0 0 1
documentation=http://www.analog.com/media/en/technical-documentation/data-sheets/AD8250.pdf
T 39200 38200 5 10 1 1 0 6 1
refdes=U203
T 38800 38000 5 10 1 1 0 0 1
value=AD8250
}
C 37900 36700 1 90 0 resistor-1.sym
{
T 37500 37000 5 10 0 0 90 0 1
device=RESISTOR
T 37900 36700 5 10 0 1 0 0 1
footprint=0603
T 37900 37200 5 10 1 1 0 0 1
refdes=R212
T 37900 37000 5 10 1 1 0 0 1
value=1M
}
C 38000 36700 1 180 0 generic-power.sym
{
T 37800 36450 5 10 1 1 180 3 1
net=AGND:1
}
C 39300 36200 1 90 0 capacitor-1.sym
{
T 38600 36400 5 10 0 0 90 0 1
device=CAPACITOR
T 38400 36400 5 10 0 0 90 0 1
symversion=0.1
T 39300 36200 5 10 0 1 0 0 1
footprint=0603
T 38600 36400 5 10 1 1 0 0 1
refdes=C208
T 38600 36200 5 10 1 1 0 0 1
value=100n
}
C 39300 36200 1 180 0 generic-power.sym
{
T 39100 35950 5 10 1 1 180 3 1
net=AGND:1
}
C 38900 37100 1 180 0 generic-power.sym
{
T 38700 36850 5 10 1 1 180 3 1
net=-15V:1
}
C 39700 37200 1 180 0 generic-power.sym
{
T 39500 36950 5 10 1 1 180 3 1
net=DGND:1
}
N 39500 37200 39500 37500 4
N 39900 37200 39900 37700 4
N 39100 37100 39100 37300 4
N 38700 37100 39100 37100 4
C 38700 40100 1 270 0 capacitor-1.sym
{
T 39400 39900 5 10 0 0 270 0 1
device=CAPACITOR
T 39600 39900 5 10 0 0 270 0 1
symversion=0.1
T 38700 40100 5 10 0 1 180 0 1
footprint=0603
T 38400 39900 5 10 1 1 0 0 1
refdes=C207
T 38400 39700 5 10 1 1 0 0 1
value=100n
}
C 38700 40100 1 0 0 generic-power.sym
{
T 38900 40350 5 10 1 1 0 3 1
net=AGND:1
}
C 38300 39200 1 0 0 generic-power.sym
{
T 38500 39450 5 10 1 1 0 3 1
net=+15V:1
}
N 38900 39200 38900 39000 4
N 38500 39200 38900 39200 4
C 39200 40200 1 270 0 input-2.sym
{
T 39900 39600 5 10 0 0 270 0 1
device=none
T 39300 39700 5 10 0 1 270 7 1
value=INPUT
T 39200 40400 5 10 1 1 270 0 1
net=INA_A0:1
}
C 39400 40100 1 270 0 input-2.sym
{
T 40100 39500 5 10 0 0 270 0 1
device=none
T 39500 39600 5 10 0 1 270 7 1
value=INPUT
T 39400 40300 5 10 1 1 270 0 1
net=INA_A1:1
}
C 39600 40000 1 270 0 input-2.sym
{
T 40300 39400 5 10 0 0 270 0 1
device=none
T 39700 39500 5 10 0 1 270 7 1
value=INPUT
T 39700 40700 5 10 1 1 270 0 1
net=INA_WR_FBO:1
}
C 41600 38200 1 180 0 resistor-1.sym
{
T 41300 37800 5 10 0 0 180 0 1
device=RESISTOR
T 41600 38200 5 10 0 1 90 0 1
footprint=0603
T 40900 38300 5 10 1 1 0 0 1
refdes=R213
T 41300 38300 5 10 1 1 0 0 1
value=49.9*
}
N 40500 38100 40700 38100 4
N 41600 38100 42500 38100 4
N 36700 38000 36700 37600 4
N 36700 37600 38500 37600 4
N 37100 38500 38500 38500 4
C 42200 37200 1 90 0 capacitor-1.sym
{
T 41500 37400 5 10 0 0 90 0 1
device=CAPACITOR
T 41300 37400 5 10 0 0 90 0 1
symversion=0.1
T 42200 37200 5 10 0 1 0 0 1
footprint=0603
T 41500 37400 5 10 1 1 0 0 1
refdes=C209
T 41500 37200 5 10 1 1 0 0 1
value=300p
}
C 42800 36200 1 0 0 jumper-1.sym
{
T 43100 36700 5 8 0 0 0 0 1
device=JUMPER
T 43100 36600 5 10 0 1 0 0 1
footprint=solderbridge
T 43100 36900 5 10 1 1 0 0 1
refdes=B203
}
N 42900 37200 42900 37600 4
N 39900 37200 42900 37200 4
C 28800 43700 1 90 0 tvs.sym
{
T 28200 44100 5 10 0 0 90 0 1
device=ZENER_DIODE
T 28200 44300 5 10 1 1 0 0 1
refdes=Z200
T 27400 44000 5 10 1 1 0 0 1
value=SMCJ15CA
T 28800 43700 5 10 0 1 0 0 1
footprint=DO214AB
T 28800 43700 5 10 0 1 0 0 1
documentation=http://www.littelfuse.com/products/tvs-diodes/surface-mount/~/media/electronics/datasheets/tvs_diodes/littelfuse_tvs_diode_smcj_datasheet.pdf.pdf
}
C 42900 43300 1 90 0 tvs.sym
{
T 42300 43700 5 10 0 0 90 0 1
device=ZENER_DIODE
T 42300 43900 5 10 1 1 0 0 1
refdes=Z202
T 41500 43600 5 10 1 1 0 0 1
value=SMCJ15CA
T 42900 43300 5 10 0 1 0 0 1
footprint=DO214AB
T 42900 43300 5 10 0 1 0 0 1
documentation=http://www.littelfuse.com/products/tvs-diodes/surface-mount/~/media/electronics/datasheets/tvs_diodes/littelfuse_tvs_diode_smcj_datasheet.pdf.pdf
}
C 42700 37200 1 90 0 tvs.sym
{
T 42100 37600 5 10 0 0 90 0 1
device=ZENER_DIODE
T 42100 37800 5 10 1 1 0 0 1
refdes=Z203
T 41300 37500 5 10 1 1 0 0 1
value=SMCJ15CA
T 42700 37200 5 10 0 1 0 0 1
footprint=DO214AB
T 42700 37200 5 10 0 1 0 0 1
documentation=http://www.littelfuse.com/products/tvs-diodes/surface-mount/~/media/electronics/datasheets/tvs_diodes/littelfuse_tvs_diode_smcj_datasheet.pdf.pdf
}
C 28600 37600 1 90 0 tvs.sym
{
T 28000 38000 5 10 0 0 90 0 1
device=ZENER_DIODE
T 28000 38200 5 10 1 1 0 0 1
refdes=Z201
T 27200 37900 5 10 1 1 0 0 1
value=SMCJ15CA
T 28600 37600 5 10 0 1 0 0 1
footprint=DO214AB
T 28600 37600 5 10 0 1 0 0 1
documentation=http://www.littelfuse.com/products/tvs-diodes/surface-mount/~/media/electronics/datasheets/tvs_diodes/littelfuse_tvs_diode_smcj_datasheet.pdf.pdf
}
C 28800 42800 1 90 0 tvs.sym
{
T 28200 43200 5 10 0 0 90 0 1
device=ZENER_DIODE
T 28200 43400 5 10 1 1 0 0 1
refdes=Z204
T 27400 43100 5 10 1 1 0 0 1
value=SMCJ15CA
T 28800 42800 5 10 0 1 0 0 1
footprint=DO214AB
T 28800 42800 5 10 0 1 0 0 1
documentation=http://www.littelfuse.com/products/tvs-diodes/surface-mount/~/media/electronics/datasheets/tvs_diodes/littelfuse_tvs_diode_smcj_datasheet.pdf.pdf
}
N 28600 42800 28900 42800 4
N 28400 36700 28700 36700 4
C 28600 36700 1 90 0 tvs.sym
{
T 28000 37100 5 10 0 0 90 0 1
device=ZENER_DIODE
T 28000 37300 5 10 1 1 0 0 1
refdes=Z205
T 27200 37000 5 10 1 1 0 0 1
value=SMCJ15CA
T 28600 36700 5 10 0 1 0 0 1
footprint=DO214AB
T 28600 36700 5 10 0 1 0 0 1
documentation=http://www.littelfuse.com/products/tvs-diodes/surface-mount/~/media/electronics/datasheets/tvs_diodes/littelfuse_tvs_diode_smcj_datasheet.pdf.pdf
}
C 42700 36300 1 90 0 tvs.sym
{
T 42100 36700 5 10 0 0 90 0 1
device=ZENER_DIODE
T 42100 36900 5 10 1 1 0 0 1
refdes=Z207
T 41300 36600 5 10 1 1 0 0 1
value=SMCJ15CA
T 42700 36300 5 10 0 1 0 0 1
footprint=DO214AB
T 42700 36300 5 10 0 1 0 0 1
documentation=http://www.littelfuse.com/products/tvs-diodes/surface-mount/~/media/electronics/datasheets/tvs_diodes/littelfuse_tvs_diode_smcj_datasheet.pdf.pdf
}
N 42500 36300 42900 36300 4
C 42900 42400 1 90 0 tvs.sym
{
T 42300 42800 5 10 0 0 90 0 1
device=ZENER_DIODE
T 42300 43000 5 10 1 1 0 0 1
refdes=Z206
T 41500 42700 5 10 1 1 0 0 1
value=SMCJ15CA
T 42900 42400 5 10 0 1 0 0 1
footprint=DO214AB
T 42900 42400 5 10 0 1 0 0 1
documentation=http://www.littelfuse.com/products/tvs-diodes/surface-mount/~/media/electronics/datasheets/tvs_diodes/littelfuse_tvs_diode_smcj_datasheet.pdf.pdf
}
N 42700 42400 43100 42400 4
