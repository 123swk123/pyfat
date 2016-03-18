tests:
	py.test --verbose tests

test-coverage:
	python-coverage run --source pyfat.py /usr/bin/py.test --verbose tests
	python-coverage html
	xdg-open htmlcov/index.html

pylint:
	-pylint --rcfile=pylint.conf pyfat.py

clean:
	rm -rf htmlcov dist MANIFEST .coverage profile
	find . -iname '*~' -exec rm -f {} \;
	find . -iname '*.pyc' -exec rm -f {} \;

.PHONY: tests test-coverage pylint clean
