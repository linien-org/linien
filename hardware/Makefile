TARGET ?= redpid

PCB_PNG_FLAGS ?= --dpi 1200 --only-visible --use-alpha --format PNG \
	--photo-mode --photo-mask-colour purple --photo-plating gold \
	--photo-silk-colour white
PCB_PRINT_PS_FLAGS ?= --drill-helper --align-marks --media Letter --scale 1 \
	--show-legend --auto-mirror
PCB_VIEW_PS_FLAGS ?= --fill-page --outline --ps-color --drill-copper \
	--media Letter
PCB_EPS_FLAGS ?= --only-visible
PCB_GERBER_FLAGS ?= --name-style fixed
PCB_BOM_FLAGS ?= --xy-unit mil
GAF_PDF_FLAGS ?= --paper Letter --color
GERBV_EXPORT_FLAGS ?= --border=5 --dpi=1200 --antialias
MERGE_DRILL ?= 1

TSYMS := $(wildcard sym/*.tsym)
TSYMBOLS := $(TSYMS:.tsym=.sym)
SYMBOLS := $(sort $(TSYMBOLS) $(wildcard sym/*.sym))
SCHEMATICS := $(name).sch $(wildcard sym/*.sch)

TARGETS := $(TARGET).sch.pdf $(TARGET).bom \
	$(TARGET).top.png $(TARGET).bottom.png \
	$(TARGET).print.pdf $(TARGET).view.pdf \
	$(TARGET).gerber.zip \
	$(if $(MERGE_DRILL),gerber/$(TARGET).drill.cnc,)

PLUS_TARGETS := $(TARGET).eps \
	$(TARGET).gerber.top.pdf $(TARGET).gerber.bottom.pdf \
	gerber/$(TARGET).drill.cnc

all: $(TARGETS)

.PHONY: clean
clean:
	-rm -f $(TSYMBOLS) $(TARGETS) $(PLUS_TARGETS)
	-rm -f $(TARGET).gerber-stamp
	-rm -f gerber/*
	-rmdir gerber

tsymbols: $(TSYMBOLS)

check-symbols: $(TSYMBOLS)
	gsymcheck $(SYMBOLS)

symbols: $(SYMBOLS)

.PHONY: edit
edit: $(TARGET).gsch2pcb
	xgsch2pcb $<

.PHONY: sch
sch : $(TARGET).sch
	gschem $<

%.sym: %.tsym
	tragesym $< $@

#.PHONY: update-pcb
#update-pcb: symbols
#	gsch2pcb project | tee pcb.log

.PHONY: pcb
pcb: $(TARGET).pcb
	pcb $<

%.print.ps: %.pcb
	pcb -x ps $(PCB_PRINT_PS_FLAGS) --psfile $@ $<

%.view.ps: %.pcb
	pcb -x ps $(PCB_VIEW_PS_FLAGS) --psfile $@ $<

%.eps: %.pcb
	pcb -x eps $(PCB_EPS_FLAGS) --eps-file $@ $<

%.top.png: %.pcb
	pcb -x png $(PCB_PNG_FLAGS) --outfile $@ $<

%.bottom.png: %.pcb
	pcb -x png $(PCB_PNG_FLAGS) --photo-flip-x --outfile $@ $<

%.bom: %.sch
	gnetlist -g partslist3 -o $@ $<

%.pdf: %.ps
	ps2pdf $< $@

%.sch.pdf: %.sch
	# geda >= 1.9
	strace -o d gaf export $(GAF_PDF_FLAGS) --output $@ $<
	# gschem -p -s /usr/share/gEDA/scheme/print.scm -o $@ $<

%.merged-sch.pdf: $(SCHEMATICS:.sch=.sch.pdf)
	pdfjoin -o $@ $^

gerber:
	mkdir -p gerber

%.gerber-stamp : %.pcb | gerber
	pcb -x gerber $(PCB_GERBER_FLAGS) --gerberfile gerber/$* $<
	pcb -x bom $(PCB_BOM_FLAGS) --bomfile gerber/$*.bom --xyfile gerber/$*.xy $<
	touch $@

gerber/%.drill.cnc: %.gerber-stamp
	gerbv -x drill -o $@ gerber/$*.*-drill.cnc
	rm gerber/$*.*-drill.cnc

%.gerber.zip: %.gerber-stamp $(if $(MERGE_DRILL),gerber/%.drill.cnc,)
	zip -j - gerber/$*.*.gbr gerber/$*.*.cnc \
		gerber/$*.xy gerber/$*.bom \
		$(wildcard README.fab.txt) > $@

.PHONY: gerbv
gerbv: $(TARGET).gerber-stamp
	gerbv gerber/$(TARGET).*.cnc gerber/$(TARGET).*.gbr

%.gerber.top.pdf: %.gerber-stamp
	gerbv --export pdf $(GERBV_EXPORT_FLAGS) --output $@ \
		gerber/$*.*.cnc \
 		$(wildcard gerber/$*.outline.gbr) \
 		$(wildcard gerber/$*.topsilk.gbr) \
 		$(wildcard gerber/$*.topmask.gbr) \
 		$(wildcard gerber/$*.top.gbr)

%.gerber.bottom.pdf: %.gerber-stamp
	gerbv --export pdf $(GERBV_EXPORT_FLAGS) --output $@ \
		gerber/$*.*.cnc \
 		$(wildcard gerber/$*.outline.gbr) \
 		$(wildcard gerber/$*.bottomsilk.gbr) \
 		$(wildcard gerber/$*.bottommask.gbr) \
 		$(wildcard gerber/$*.bottom.gbr)
