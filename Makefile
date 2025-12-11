all:
	mkdir -p data/cache data/ost data/threlease
	python3 threlease.py
	python3 thbmain.py

clean:
	rm -rf data
