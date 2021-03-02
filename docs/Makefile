ifeq ($(OS),Windows_NT)
include ../Makefile.win
else
include ../Makefile.unix
endif

BUILDDIR=_build
SPHINXBUILD=sphinx-build -v -n -a

DOC_ARTIFACTS_TUTORIALS= *.py \
	*.ipynb
DOC_ARTIFACTS_EXAMPLES= hardware \
	rabi_demo \
	VQE 
DOC_ARTIFACTS_MICROMOTION= micromotion.zip
     

.PHONY: clean-examples
clean-examples:
	cd examples && $(foreach var,$(DOC_ARTIFACTS_EXAMPLES),$(RMCMD) $(var);) 

.PHONY: clean-micromotion
clean-micromotion:
	cd examples && cd micromotion && $(foreach var,$(DOC_ARTIFACTS_MICROMOTION),$(RMCMD) $(var);) 

.PHONY: clean-tutorials
clean-tutorials:
	cd tutorials && $(foreach var,$(DOC_ARTIFACTS_TUTORIALS),$(RMCMD) $(var);)

.PHONY: clean-build
clean-build: 
	$(RMCMD) $(BUILDDIR)

.PHONY: clean
clean: clean-tutorials clean-examples clean-micromotion clean-build


.PHONY: pre-build
pre-build:
	mkdir -p tutorials examples

	cp ../examples/tutorials/*.py tutorials/
	cp ../examples/tutorials/*.ipynb tutorials/

	cp -r ../examples/hardware examples/

	cp -r ../examples/rabi_demo examples/
	cd examples/rabi_demo/ && zip -r rabi_demo.zip *.py *.ipynb

	cp -r ../examples/VQE examples/

	cd ../examples/demos/micromotion/migen/ && zip -r micromotion.zip *
	mv ../examples/demos/micromotion/migen/micromotion.zip examples/micromotion/

# --------------- DOCS -------------------------------------------------------#


.PHONY: all
all: html pdf epub

.PHONY: html
html: pre-build
	$(SPHINXBUILD) -b html -w sphinx-build-html.log . $(BUILDDIR)/html/
	@echo "Build finished: HTML"

.PHONY: pdf
pdf: pre-build
	$(SPHINXBUILD) -b rinoh -w sphinx-build-pdf.log . $(BUILDDIR)/pdf/
	@echo "Build finished: PDF"

.PHONY: epub
epub: pre-build
	$(SPHINXBUILD) -b epub -w sphinx-build-epub.log . $(BUILDDIR)/epub/
	@echo "Build finished: EPUB"
