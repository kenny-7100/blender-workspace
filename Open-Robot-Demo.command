#!/bin/zsh
BLENDER_WORKSPACE=${0:A:h}
exec "$BLENDER_WORKSPACE/bin/blender" "$BLENDER_WORKSPACE/projects/robot-demo/robot.blend" "$@"
