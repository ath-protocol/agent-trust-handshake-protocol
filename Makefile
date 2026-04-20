.PHONY: dev install broken

install:
	npm install

dev:
	npx mintlify dev

broken:
	npx mintlify broken-links
