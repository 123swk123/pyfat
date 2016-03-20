tests:
	py.test --verbose tests

test-coverage:
	python-coverage run --source pyfat.py /usr/bin/py.test --verbose tests
	python-coverage html
	xdg-open htmlcov/index.html

pylint:
	-pylint --rcfile=pylint.conf pyfat.py

sdist:
	python setup.py sdist

srpm: sdist
	rpmbuild -bs pyfat.spec --define "_sourcedir `pwd`/dist"

rpm: sdist
	rpmbuild -ba pyfat.spec --define "_sourcedir `pwd`/dist"

clean:
	rm -rf htmlcov dist MANIFEST .coverage profile
	find . -iname '*~' -exec rm -f {} \;
	find . -iname '*.pyc' -exec rm -f {} \;

.PHONY: tests test-coverage pylint sdist srpm rpm clean
