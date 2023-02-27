# todo: this horrible thing is needed to deal with an back incompat thing in notanorm
NOTANORM := $(shell pip freeze | grep notanorm)

env:
	python -mvirtualenv env

requirements:
	python -mpip install --isolated -r requirements.txt

lint:
	python -m pylint snostr
	black snostr

black:
	black snostr tests

test:
	pytest -n=3 --cov snostr -v tests

publish:
	rm -rf dist
	python3 setup.py bdist_wheel
	twine upload dist/*

install-hooks:
	pre-commit install


.PHONY: black publish requirements lint install-hooks
.DELETE_ON_ERROR:
