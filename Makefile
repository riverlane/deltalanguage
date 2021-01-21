# ----------------------------------------------------------------------------#
# --------------- MAKEFILE FOR DELTALANGUAGE ---------------------------------#
# ----------------------------------------------------------------------------#


# For reference see
# https://gist.github.com/mpneuried/0594963ad38e68917ef189b4e6a269db


# --------------- DECLARATIONS -----------------------------------------------#


.DEFAULT_GOAL := help
.PHONY: help
help: ## List of main goals
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / \
	{printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

ifeq ($(OS),Windows_NT)
  # Windows is not supported!
else
  # Some commands are different in Linux and Mac
  UNAME_S := $(shell uname -s)

  # User's credential will be passed to the image and container
  USERNAME=$(shell whoami)
  USER_UID=$(shell id -u)
  USER_GID=$(shell id -g)
endif

PWD=$(shell pwd)

IMAGENAME=deltalanguage
CONTAINERNAME=deltalanguage

DBUILD=docker build . \
	--file ./environment/Dockerfile \
	--tag ${IMAGENAME} \
	--build-arg USERNAME=${USERNAME} \
	--build-arg USER_UID=${USER_UID} \
	--build-arg USER_GID=${USER_GID}

DRUN=docker run \
	--interactive \
	--privileged \
	--rm \
	--volume ${PWD}:/workdir \
	--workdir /workdir \
	--name=${CONTAINERNAME}

DEXEC=docker exec \
	--interactive \
	$(shell cat container)

PYCODESTYLE=pycodestyle -v \
	deltalanguage/ examples/ test/ >> pycodestyle.log || true

PYLINT=pylint \
	--exit-zero \
	--rcfile=pylint.rc \
	deltalanguage/ examples/ test/ >> pylint.log

PYTHONNOSE=python -m nose \
	--with-xunit \
	--logging-level=INFO \
	--with-xcoverage \
	--cover-erase \
	--cover-package=deltalanguage \
	--verbose \
	--detailed-errors \
	--with-randomly

LICENSES=pip-licenses --format=confluence --output-file licenses.confluence && \
	echo -e '\n' >> licenses.confluence && \
	echo `date -u` >> licenses.confluence && \
	pip-licenses --format=csv --output-file licenses.csv

TESTUPLOADPACKAGE=python -m twine upload \
	--repository testpypi \
	-u $(user) \
	-p $(pass) \
	dist/*

UPLOADPACKAGE=python -m twine upload \
	-u $(user) \
	-p $(pass) \
	dist/*

MAKEPACKAGE=python setup.py sdist bdist_wheel

CHECKPACKAGE=python -m twine check dist/*

TESTPACKAGE=python setup.py test

# Passing arguments to documentation builder in docs/Makefile
# i.e. `make docs command` in ./ --> `make command` in ./docs/
# 
# For HTML documentation run `make docs html`, then
# open docs/_build/html/index.html in your favourite browser.
# 
# Ref https://stackoverflow.com/a/14061796
# Ref https://stackoverflow.com/a/9802777/3454146
FORDOCS=$(firstword $(MAKECMDGOALS))
ifeq ($(FORDOCS), $(filter $(FORDOCS), docs dev-docs))
  DOCS_ARGS := $(wordlist 2,$(words $(MAKECMDGOALS)),$(MAKECMDGOALS))
  $(eval $(DOCS_ARGS):;@:)
endif

# --------------- DOCKER STUFF -----------------------------------------------#


.PHONY: build
build: ./environment/Dockerfile ## Build the image
	${DBUILD}

.PHONY: build-nc
build-nc: ./environment/Dockerfile ## Build the image from scratch
	${DBUILD} --no-cache

# --privileged: needed for DGB, but also needed for leaksan,
# so causes a heisenbug: lsan throws a warning, enabling --priv fixes it
container: ## Spin out the container
	# if `build` is put in dependencies then it will cause rerun of `container`,
	# we want it to be blocked by `container` file though
	make build
	${DRUN} \
	--detach \
	--cidfile=container \
	${IMAGENAME} \
	/bin/bash

.PHONY: rshell
rshell: container
	docker exec --privileged -it $(shell cat container) /bin/bash

.PHONY: shell
shell: container
	docker exec -it $(shell cat container) /bin/bash

.PHONY: notebook
notebook: container ## Attach a Jupyter Notebook to a container
	${DRUN} \
	--publish 5698:5698 \
	${IMAGENAME} \
	jupyter notebook \
	--port 5698 \
	--no-browser \
	--ip=0.0.0.0


# --------------- DOCUMENTATION ----------------------------------------------#

.ONESHELL:
.PHONY: licenses
licenses: container ## Generate license info
	${DEXEC} bash -c "${LICENSES}"

.PHONY: docs
docs: container ## Generate docs
	${DEXEC} make -C docs $(DOCS_ARGS)


# --------------- TESTING ----------------------------------------------------#


.PHONY: test
test: test-nose ## Run all the tests

.PHONY: test-nose
test-nose: container ## Run the test suite via nose
	${DEXEC} ${PYTHONNOSE}

.PHONY: test-unit
test-unit: container ## Run the test suite via unittest
	${DEXEC} python -m unittest discover

.PHONY: check-os
check-os: ## Which OS is used?
ifeq ($(OS),Windows_NT)
	@echo MAKEFILE: Windows is detected (not supported!)
else ifeq ($(UNAME_S),Linux)
	@echo MAKEFILE: Linux is detected
else ifeq ($(UNAME_S),Darwin)
	@echo MAKEFILE: Mac is detected
else
	@echo MAKEFILE: What is this beast?
endif


# --------------- QA ---------------------------------------------------------#


.PHONY: pylint
pylint: container ## Run code quality checker
	${DEXEC} ${PYLINT}

.PHONY: pycodestyle
pycodestyle: container ## Run PEP8 checker
	${DEXEC} ${PYCODESTYLE}


# --------------- PACKAGING --------------------------------------------------#


.PHONY: build-package
build-package: clean-package container ## Make the package
	${DEXEC} ${MAKEPACKAGE}
	${DEXEC} ${CHECKPACKAGE}

.PHONY: test-upload-package
test-upload-package: build-package ## Make and upload the package to test.pypi.org
	${DEXEC} ${TESTUPLOADPACKAGE}

.PHONY: upload-package
upload-package: build-package ## Make and upload the package to pypi.org
	${DEXEC} ${UPLOADPACKAGE}

.PHONY: test-package
test-package: ## Make and run tests on the package
	${DEXEC} ${TESTPACKAGE}


# --------------- CLEANING ---------------------------------------------------#


.PHONY: clean
clean: dev-clean clean-container ## Clean everything

.PHONY: clean-cache
clean-cache: ## Clean python cache
ifeq ($(UNAME_S),Linux)
	find . -name "__pycache__" -type d -print0 | xargs -r0 -- rm -r
	find . -name "*.pyc" -type f -print0 | xargs -r0 -- rm -r
else
	find . -name "*.pyc" -type f -exec rm -rf {} \;
	find . -name "__pycache__" -type d -exec rm -rf {} \;
endif

.PHONY: clean-container
clean-container: ## Stop and remove the container
	docker ps -q --filter "name=${CONTAINERNAME}" | grep -q . && \
	docker stop ${CONTAINERNAME}
	rm -f container

.PHONY: clean-cover
clean-cover: ## Clean the test suite results
	rm -f .coverage coverage.xml nosetests.xml trace.vcd

.PHONY: clean-data
clean-data: ## Clean any data
ifeq ($(UNAME_S),Linux)
	find . -name "printed_graph.df" -type f -print0 | xargs -r0 -- rm -r
else
	find . -name "printed_graph.df" -exec rm -rf {} \;
endif
	rm -f *.vcd *.png *.txt

.PHONY: clean-docs
clean-docs: ## Clean docs
	make -C docs clean

.PHONY: clean-licenses
clean-licenses: ## Clean licenses
	rm -f licenses.confluence licenses.csv

.PHONY: clean-logs
clean-logs: ## Clean logs
	rm -f pylint.log pycodestyle.log docs/sphinx-build-*.log

.PHONY: clean-package
clean-package: ## Clean packaging artifacts
	rm -rf dist *.egg-info .eggs build


# --------------- DEVELOPMENT ------------------------------------------------#


# Commands from this section are meant to be used ONLY inside of
# the development container via VSCode

.PHONY: dev-test
dev-test: dev-test-nose ## See non-dev version

.PHONY: dev-test-nose
dev-test-nose: ## See non-dev version
	${PYTHONNOSE}

.PHONY: dev-test-unit
dev-test-unit: ## See non-dev version
	python -m unittest discover

.ONESHELL:
.PHONY: dev-licenses
dev-licenses: ## See non-dev version
	${LICENSES}

.PHONY: dev-docs
dev-docs: ## See non-dev version
	make -C docs $(DOCS_ARGS)

.PHONY: dev-pylint
dev-pylint: ## See non-dev version
	${PYLINT}

.PHONY: dev-pycodestyle
dev-pycodestyle: ## See non-dev version
	${PYCODESTYLE}

.PHONY: dev-build-package
dev-build-package: clean-package ## See non-dev version
	${MAKEPACKAGE}
	${CHECKPACKAGE}

.PHONY: dev-upload-package
dev-upload-package: dev-build-package ## See non-dev version
	${UPLOADPACKAGE}

.PHONY: dev-test-upload-package
dev-test-upload-package: dev-build-package ## See non-dev version
	${TESTUPLOADPACKAGE}

.PHONY: dev-test-package
dev-test-package: ## See non-dev version
	${TESTPACKAGE}

.PHONY: dev-clean
dev-clean: clean-cache clean-cover clean-data clean-licenses clean-logs clean-docs clean-package ## See non-dev version
