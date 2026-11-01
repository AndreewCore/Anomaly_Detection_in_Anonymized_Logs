# Compila las herramientas en C. Los binarios están en .gitignore: se regeneran aquí.
CC      ?= gcc
CFLAGS  ?= -O2 -Wall -Wextra
LDFLAGS ?= -pthread

BINS = agente anomalia

.PHONY: all clean

all: $(BINS)

%: %.c
	$(CC) $(CFLAGS) -o $@ $< $(LDFLAGS)

clean:
	rm -f $(BINS) *.o
