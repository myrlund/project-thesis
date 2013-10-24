#!/bin/bash

FILENAME=${1:-main}

echo Compiling $FILENAME.

pdflatex $FILENAME.tex
bibtex   $FILENAME.aux
pdflatex $FILENAME.tex
pdflatex $FILENAME.tex

echo Done.
