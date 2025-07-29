all: run

.PHONY: run compile

run: compile
	./main

compile: main.c3 talib.c3
	c3c compile main.c3 talib.c3 -l ./ta-lib-0.6.4/src/.libs/libta-lib.a

