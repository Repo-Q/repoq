.PHONY: build run sample

build:
	docker build -t repoq:3.0 .

run:
	docker run --rm -v $$(pwd):/repo -w /repo repoq:3.0 full . -o out/quality.jsonld --md out/quality.md --graphs graphs/ --certs certs/ --zag-out zag/

sample:
	python -m repoq.cli --help
