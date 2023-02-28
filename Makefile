# todo: this horrible thing is needed to deal with an back incompat thing in notanorm
NOTANORM := $(shell pip freeze | grep notanorm)

env:
	python -mvirtualenv env
	mkdir env/bin 2> /dev/null || true

wheel-env:
	python -mvirtualenv wheel-env
	mkdir wheel-env/bin 2> /dev/null || true

requirements: env
	python -mpip install --isolated -r requirements.txt

lint:
	python -m pylint snostr
	black snostr

black:
	black snostr tests

test:
	pytest -n=3 --cov snostr -v tests

dist:
	rm -rf dist
	python -m build .

test-wheel: wheel-env
	cp wheel-env/scripts/activate wheel-env/bin/activate 2> /dev/null || true
	. wheel-env/bin/activate && pip install .
	. wheel-env/bin/activate && snostr --self-test

publish: dist
	twine upload dist/*

install-hooks:
	pre-commit install


.PHONY: black publish requirements lint install-hooks dist
.DELETE_ON_ERROR:
