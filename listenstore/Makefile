.PHONY: lint dist dist_stripped clean

dist:
	python setup.py bdist_egg

dist_stripped:
	python setup.py bdist_egg --exclude-source-files -d dist_stripped

clean:
	rm -Rf ./listenstore.egg-info
	rm -Rf ./dist ./dist_stripped
	find ./listenstore/ -name '*.pyc' -exec rm {} \;

lint:
	PYFLAKES_NODOCTEST=1 flake8 --max-complexity=10 --max-line-length=110 --ignore=W191,C901 ./listenstore

test:
	tox
