tests:
	py.test --verbose tests

pylint:
	-pylint --rcfile=pylint.conf pyfat.py

clean:
	rm -rf htmlcov dist MANIFEST .coverage profile
	find . -iname '*~' -exec rm -f {} \;
	find . -iname '*.pyc' -exec rm -f {} \;

.PHONY: tests pylint clean
