# ROS TF example

TODO: INSERT SOME COOL IMAGE OR VIDEO

## Used Rerun types

[`Transform3D`](https://www.rerun.io/docs/reference/types/archetypes/transform3d), [`CoordinateFrame`](https://rerun.io/docs/reference/types/archetypes/coordinate_frame), [`Pinhole`](https://rerun.io/docs/reference/types/archetypes/pinhole), [`ViewCoordinates`](https://rerun.io/docs/reference/types/archetypes/view_coordinates), [`InstancePoses3D`](https://rerun.io/docs/reference/types/archetypes/instance_poses3d)

## Overview

ROS 2 uses the transform library, [tf2](https://docs.ros.org/en/jazzy/Concepts/Intermediate/About-Tf2.html), to track multiple coordinate frames over time. It is a powerful system that allows developers to transform points, vectors, and poses between different frames of reference (e.g., from a "camera_link" to "base_link"). This system makes collaboration between developers around the world easier, as it provides a common language for how transforms should be handled — a topic that can otherwise be defined in many different ways.

This example demonstrates how Rerun seamlessly integrates with the ROS transform system, allowing you to visualize robot hierarchies and sensor data with zero-to-minimal configuration.

**What you will learn**:

1. **Direct Playback**: Play a rosbag directly in the Rerun viewer. This demonstrates how [`tf2_msgs/msg/TFMessage`](https://docs.ros.org/en/jazzy/p/tf2_msgs/msg/TFMessage.html) are automatically converted to [`Transform3D`](https://www.rerun.io/docs/reference/types/archetypes/transform3d) and a ROS message's `frame_id` are converted to [`CoordinateFrame`](https://rerun.io/docs/reference/types/archetypes/coordinate_frame), making it possible to easily view a rosbag in Rerun without any code.
2. **Python Integration**: Read a rosbag from Python and use the [`tf2_msgs/msg/TFMessage`](https://docs.ros.org/en/jazzy/p/tf2_msgs/msg/TFMessage.html) and the different ROS topic's `frame_id` to correctly display the content in the Rerun viewer.

## Useful resources

Below you will find a collection of useful Rerun resources for this example:

* [Concepts — Transforms & Coordinate Frames](https://rerun.io/docs/concepts/logging-and-ingestion/transforms)
  * Highly recommend reading to understand how Rerun defines and handles transforms and coordinate frames. Rerun's system has both similarities and differences to the system ROS uses and reading this page will help you grasp these similarities and differences. You will also see how flexible and powerful Rerun's system is.
* [How-to — Use Rerun with ROS 2](https://rerun.io/docs/howto/integrations/ros2-nav-turtlebot)
  * A practical guide for ROS 2 integration. For this example, it can be good to, at least, read the section [TF to rr.Transform3D](https://rerun.io/docs/howto/integrations/ros2-nav-turtlebot#tf-to-rrtransform3d).
* [MCAP — ROS 2 transforms (TF)](https://rerun.io/docs/concepts/logging-and-ingestion/mcap/message-formats#ros-2-transforms-tf)
  * Describes the technical conversion of [`tf2_msgs/msg/TFMessage`](https://docs.ros.org/en/jazzy/p/tf2_msgs/msg/TFMessage.html) to [`Transform3D`](https://www.rerun.io/docs/reference/types/archetypes/transform3d) when using MCAP's in Rerun.
* [MCAP — ROS 2 poses and frame IDs](https://rerun.io/docs/concepts/logging-and-ingestion/mcap/message-formats#ros-2-poses-and-frame-ids)
  * Describes the technical conversion of a message's header frame ID to [`CoordinateFrame`](https://rerun.io/docs/reference/types/archetypes/coordinate_frame) when using MCAP's in Rerun.

## Play a rosbag directly in the viewer

The simplest way to use ROS data in Rerun is to drag-and-drop an **MCAP** file directly into the viewer.

> Note: If you are using ROS 1 (`.bag`) or ROS 2 SQLite3 (`.db3`) files, convert them to MCAP first using the [MCAP CLI](https://mcap.dev/guides/cli) or the [Rosbags](https://ternaris.gitlab.io/rosbags/) tool (see the [MCAP example](https://github.com/rerun-io/mcap_example) for more in-depth explaination).

Rerun automatically convert [`tf2_msgs/msg/TFMessage`](https://docs.ros.org/en/jazzy/p/tf2_msgs/msg/TFMessage.html) messages into [`Transform3D`](https://www.rerun.io/docs/reference/types/archetypes/transform3d), with `parent_frame` and `child_frame` set to the message's `frame_id` and `child_frame_id`. The timestamsp are put onto the `ros2_*` timelines. For other supported messages, if they have a [`std_msgs/msg/Header`](https://docs.ros.org/en/jazzy/p/std_msgs/msg/Header.html) a [`CoordinateFrame`](https://rerun.io/docs/reference/types/archetypes/coordinate_frame) is created using the `frame_id` from the message's header.

## Read rosbags from Python

Sometimes you want to perform processing on the rosbag before viewing the data. This example shows how to load the bag in Python, read the ROS transforms, and use header frame IDs to correctly display them in the Rerun viewer.
