PYTHON_SOURCES = *.py .github terraform

.PHONY: tidy
tidy:
	terraform fmt -recursive
	isort --recursive $(PYTHON_SOURCES)
	black $(PYTHON_SOURCES)
	flake8 --ignore E501 $(PYTHON_SOURCES)

.PHONY: test
test:
	pytest -v
