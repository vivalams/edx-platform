#!/usr/bin/env bash

docker exec -i devstack /bin/bash -s <<EOF

export LC_ALL=en_US.utf8
export LANG=en_US.utf8
export LANGUAGE=en_US.utf8

# Elevate priveleges to edxapp user
echo 'Run as edxapp user'
sudo su edxapp -s /bin/bash 
source /edx/app/edxapp/edxapp_env
cd /edx/app/edxapp/edx-platform

# These variables are becoming unset inside docker container
export CODE_COV_TOKEN=$CODE_COV_TOKEN
export TRAVIS=true

<<<<<<< HEAD
# Get the diff coverage and html reports for unit tests
paver coverage
=======
git pull
# Get the diff coverage and html reports for unit tests
paver coverage --compare-branch=origin/$TRAVIS_BRANCH
>>>>>>> 416f36a34c40fc1a612d7b03f1bdeb61be81e6b0

pip install codecov==2.0.5
codecov --token=$CODE_COV_TOKEN --branch=$BRANCH
EOF
