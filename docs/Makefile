BUILDDIR=_build
SPHINXBUILD=sphinx-build -v -n -a


.PHONY: clean
clean:
	rm -rf $(BUILDDIR)/*
	rm -f tutorials/*.py tutorials/*.ipynb
	rm -rf examples/hardware
	rm -rf examples/rabi_demo
	rm -rf examples/VQE

.PHONY: pre-build
pre-build:
	mkdir -p tutorials examples
	cp ../examples/tutorials/*.py tutorials/
	cp ../examples/tutorials/*.ipynb tutorials/
	cp -r ../examples/hardware examples/
	cp -r ../examples/rabi_demo examples/
	cp -r ../examples/VQE examples/

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
