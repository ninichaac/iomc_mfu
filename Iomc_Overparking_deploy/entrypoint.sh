#!/bin/bash
xhost +local:docker
exec "$@"