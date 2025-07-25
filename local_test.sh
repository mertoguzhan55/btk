#!/bin/sh
pylint app/ tests/ app.py
if [ $? -eq 0 ]; then
    echo "###################"
    echo "Quality test passed"
    echo "###################"
else
    echo "###################"
    echo "Quality test fail"
    echo "###################"
    exit
fi

pytest
if [ $? -eq 0 ]; then
    echo "###################"
    echo "Unit test passed"
    echo "###################"
else
    echo "###################"
    echo "Unit test fail"
    echo "###################"
    exit
fi

python app.py --env local
if [ $? -eq 0 ]; then
    echo "###################"
    echo "end2end test passed."
    echo "###################"
else
    echo "###################"
    echo "end2end test fail."
    echo "###################"
    exit
fi

docker build --tag base .
if [ $? -eq 0 ]; then
    echo "###################"
    echo "Docker build test passed."
    echo "###################"
else
    echo "###################"
    echo "Docker build test fail."
    echo "###################"
    exit
fi