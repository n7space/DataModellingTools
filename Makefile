PY_SRC:=$(wildcard dmt/asn2dataModel.py dmt/aadl2glueC.py dmt/smp2asn.py dmt/*mappers/[a-zA-Z]*py dmt/commonPy/[a-zA-Z]*py)
PY_SRC:=$(filter-out dmt/B_mappers/antlr.main.py dmt/A_mappers/Stubs.py dmt/B_mappers/micropython_async_B_mapper.py dmt/commonPy/commonSMP2.py, ${PY_SRC})
PY_SRC:=$(filter-out dmt/B_mappers/vhdlTemplate.py dmt/B_mappers/vhdlTemplateZynQZC706.py dmt/B_mappers/vhdlTemplateBrave.py dmt/B_mappers/vhdlTemplateZestSC1.py, ${PY_SRC})

all:	tests

tests:	flake8 pylint mypy coverage testDB

configure:
	./configure

install:	configure
	python3 -m pip uninstall -y dmt || exit 0  # Uninstall if there, but don't abort if not installed
	python3 -m pip install --user .

flake8:
	@echo Performing syntax checks via flake8...
	@flake8 ${PY_SRC} || exit 1

pylint:
	@echo Performing static analysis via pylint...
	@pylint --disable=I --rcfile=pylint.cfg ${PY_SRC}

mypy:
	@echo Performing type analysis via mypy...
	@mypy ${PY_SRC} || exit 1

coverage:
	@echo Performing coverage checks...
	@$(MAKE) -C tests-coverage  || exit 1

testDB:
	@echo Installing DMT for local user...
	@python3 -m pip install .
	@echo Performing database tests...
	@$(MAKE) -C tests-sqlalchemy  || exit 1

.PHONY:	flake8 pylint mypy coverage install configure
