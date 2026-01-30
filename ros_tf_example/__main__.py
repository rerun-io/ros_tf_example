#!/usr/bin/env python3

import rerun as rr
import rerun.blueprint as rrb

import argparse
import pathlib
from typing import Final

from datafusion import col
import numpy as np
import matplotlib as mpl
import pyarrow as pa

DESCRIPTION = """
# ROS TF Example

ROS 2 uses the transform library, [tf2](https://docs.ros.org/en/jazzy/Concepts/Intermediate/About-Tf2.html), to track multiple coordinate frames over time. It is a powerful system that allows developers to transform points, vectors, and poses between different frames of reference (e.g., from a "camera_link" to "base_link"). This system makes collaboration between developers around the world easier, as it provides a common language for how transforms should be handled — a topic that can otherwise be defined in many different ways. In Rerun, you can use [named transforms](https://rerun.io/docs/concepts/logging-and-ingestion/transforms#named-transform-frames) to decouple spatial relationships from the entity hierarchy, similar to as it is done in ROS.

The Rerun documentation already contain guides for how to work with named transforms and how to turn your ROS 2 transforms into Rerun transforms. Instead of repeating the documentation, this example will show you how to debug your system when transforms do not work.
"""

EXAMPLE_DIR: Final = pathlib.Path(__file__).parent.parent

# Helper functions

def get_timestamps(df, timeline: str) -> np.ndarray:
    return pa.table(df.select(timeline))[timeline].to_numpy()


def get_frames(df, frame_col: str) -> list[str]:
    return pa.table(df.select(frame_col))[frame_col].to_pylist()


def log_frames(entity: str, timestamps: rr.TimeColumn, frame: list[str]) -> None:
    rr.send_columns(
        entity,
        indexes=[timestamps],
        columns=rr.CoordinateFrame.columns(
            frame=frame,
        ),
    )


def log_dataset(path_to_rrd: pathlib.Path) -> None:
    """Log the dataset from the given RRD file.

    :param path_to_rrd: The path to the RRD file.
    :type path_to_rrd: pathlib.Path
    """

    with rr.server.Server(datasets={'dataset': [path_to_rrd]}) as server:
        dataset = server.client().get_dataset('dataset')

        log_transforms(dataset)
        log_gps(dataset)
        log_camera(dataset)
        log_images(dataset)
        log_point_clouds(dataset)


def log_transforms(dataset: rr.catalog.DatasetEntry) -> None:
    """Log TF transforms from the dataset.

    :param dataset: The dataset containing TF information.
    :type dataset: rr.catalog.DatasetEntry
    """

    entity = '/tf'
    child_frame_col = f'{entity}:Transform3D:child_frame'
    parent_frame_col = f'{entity}:Transform3D:parent_frame'
    quaternion_col = f'{entity}:Transform3D:quaternion'
    translation_col = f'{entity}:Transform3D:translation'
    timeline = 'ros2_timestamp'

    df = dataset.filter_contents([entity]).reader(index=timeline)

    timestamps = rr.TimeColumn('time', timestamp=get_timestamps(df, timeline))

    translation = pa.table(df.select(col(translation_col)[0]))[0].to_pylist()
    quaternion = pa.table(df.select(col(quaternion_col)[0]))[0].to_pylist()
    child_frame = pa.table(df.select(col(child_frame_col)[0]))[0].to_pylist()
    parent_frame = pa.table(df.select(col(parent_frame_col)[0]))[0].to_pylist()

    # Remove leading slashes
    child_frame = [frame[1:] if frame.startswith(
        '/') else frame for frame in child_frame]
    parent_frame = [frame[1:] if frame.startswith(
        '/') else frame for frame in parent_frame]

    rr.send_columns(
        'tf',
        indexes=[timestamps],
        columns=rr.Transform3D.columns(
            translation=translation,
            quaternion=quaternion,
            child_frame=child_frame,
            parent_frame=parent_frame,
        ),
    )

    rr.log('tf', rr.TransformAxes3D(
        axis_length=0.25, show_frame=True), static=True)


    # Also log arrows for each transform for easier debugging
    
    for stamp, p, c, t in zip(timestamps.times, parent_frame, child_frame, translation):
        rr.set_time('time', timestamp=stamp)
        rr.log(
            f'tf/{p}/{c}',
            rr.CoordinateFrame(frame=p),
            rr.Arrows3D(
                vectors=[t],
                labels=[f'{p} -> {c}'],
                show_labels=False,
            )
        )

        if p == 'map' and c == 'gps':
            # print(q)
            rr.log(
                'tf',
                rr.Transform3D(
                    translation=t,
                    parent_frame=p,
                    child_frame=f'{c}_fix_rot',
                ),
            )
            rr.log(
                f'tf/{p}/{c}_fix_rot',
                rr.CoordinateFrame(frame=p),
                rr.Arrows3D(
                    vectors=[t],
                    labels=[f'{p} -> {c}_fix_rot'],
                    show_labels=False,
                )
            )

    rr.log("/", rr.CoordinateFrame("map"), static=True)


def log_gps(dataset: rr.catalog.DatasetEntry) -> None:
    """Log GPS data from the dataset.

    :param dataset: The dataset containing GPS information.
    :type dataset: rr.catalog.DatasetEntry
    """

    entity = '/gps/duro/fix'
    coordinate_frame_col = f'{entity}:CoordinateFrame:frame'
    positions_col = f'{entity}:GeoPoints:positions'
    timeline = 'ros2_timestamp'

    df = dataset.filter_contents([entity]).reader(index=timeline)

    timestamps = rr.TimeColumn('time', timestamp=get_timestamps(df, timeline))
    frame = get_frames(df, coordinate_frame_col)

    positions = pa.table(df.select(col(positions_col)[0]))[0].to_pylist()

    log_frames(entity, timestamps, frame)

    rr.send_columns(
        entity,
        indexes=[timestamps],
        columns=rr.GeoPoints.columns(
            positions=positions,
            radii=[rr.Radius.ui_points(10.0)] * len(positions),
            # TODO: Not working: colors=[(1, 0, 0, 1)] * len(positions),
        ),
    )


def log_camera(dataset: rr.catalog.DatasetEntry) -> None:
    """Log camera data, the pinhole camera, from the dataset. Also, add a transform for the camera.

    :param dataset: The dataset containing camera information.
    :type dataset: rr.catalog.DatasetEntry
    """

    entity = '/zed_node/left/camera_info'
    # parent_frame_col = f'{entity}:Pinhole:parent_frame'
    # child_frame_col = f'{entity}:Pinhole:child_frame'
    resolution_col = f'{entity}:Pinhole:resolution'
    image_from_camera_col = f'{entity}:Pinhole:image_from_camera'
    timeline = 'ros2_timestamp'

    df = dataset.filter_contents([entity]).reader(index=timeline)

    timestamps = rr.TimeColumn('time', timestamp=get_timestamps(df, timeline))

    # parent_frame = pa.table(df.select(col(parent_frame_col)[0]))[0].to_pylist()
    # child_frame = pa.table(df.select(col(child_frame_col)[0]))[0].to_pylist()
    resolution = pa.table(df.select(col(resolution_col)[0]))[0].to_pylist()
    image_from_camera = pa.table(df.select(col(image_from_camera_col)[0]))[0].to_pylist()

    image_from_camera = np.array(image_from_camera).reshape(-1, 3, 3, order='F')

    rr.send_columns(
        f'{entity}',
        indexes=[timestamps],
        columns=rr.Pinhole.columns(
            image_from_camera=image_from_camera,
            camera_xyz=[rr.components.ViewCoordinates.FLU] * len(image_from_camera),
            resolution=resolution,
            child_frame=['zed_camera_front_image_plane'] * len(image_from_camera),
            parent_frame=['zed_camera_front'] * len(image_from_camera),
            image_plane_distance=[1.0] * len(image_from_camera),
        ),
    )


def log_images(dataset: rr.catalog.DatasetEntry) -> None:
    """Log image data from the dataset.

    :param dataset: The dataset containing image information.
    :type dataset: rr.catalog.DatasetEntry
    """

    entity = '/zed_node/left/image_rect_color/compressed'
    coordinate_frame_col = f'{entity}:CoordinateFrame:frame'
    blob_col = f'{entity}:EncodedImage:blob'
    timeline = 'ros2_timestamp'

    df = dataset.filter_contents([entity]).reader(index=timeline)

    timestamps = rr.TimeColumn('time', timestamp=get_timestamps(df, timeline))
    frame = get_frames(df, coordinate_frame_col)

    images = pa.table(df.select(blob_col))[blob_col].to_numpy()
    images = np.concatenate(images).tolist()

    log_frames(entity, timestamps, frame)

    rr.send_columns(
        entity,
        indexes=[timestamps],
        columns=rr.EncodedImage.columns(
            blob=images,
        ),
    )

    rr.log(entity, rr.CoordinateFrame(frame='zed_camera_front_image_plane'), static=True)

def log_point_clouds(dataset: rr.catalog.DatasetEntry) -> None:
    """Log point cloud data from the dataset.

    :param dataset: The dataset containing point cloud information.
    :type dataset: rr.catalog.DatasetEntry
    """

    entity = '/left_os1/os1_cloud_node/points'
    coordinate_frame_col = f'{entity}:CoordinateFrame:frame'
    positions_col = f'{entity}:Points3D:positions'
    timeline = 'ros2_timestamp'

    df = dataset.filter_contents([entity]).reader(index=timeline)

    for stream in df.select(timeline, coordinate_frame_col, positions_col).repartition(10).execute_stream_partitioned():
        for batch in stream:
            pa = batch.to_pyarrow()
            for i in range(pa.num_rows):
                frame = pa[coordinate_frame_col][i].as_py()[0]
                positions = np.array(pa[positions_col][i].as_py())

                min_z = np.min(positions[:, 2])
                max_z = np.max(positions[:, 2])
                colors = (positions[:, 2] - min_z) / (max_z - min_z)
                colors = mpl.colormaps['turbo'](colors)[:, :3]

                rr.set_time('time', timestamp=pa[timeline][i])
                rr.log(entity, rr.CoordinateFrame(frame))
                rr.log(
                    entity,
                    rr.Points3D(
                        positions=positions,
                        colors=colors,
                        radii=rr.Radius.ui_points(2.0),
                    ),
                )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="ROS TF example.")
    parser.add_argument(
        "--root-dir",
        type=pathlib.Path,
        default=EXAMPLE_DIR,
        help="Root directory of the dataset",
    )
    parser.add_argument(
        "--dataset-file",
        type=str,
        default="leaf-2022-03-18-gyor.rrd",
        help="The dataset file to visualize",
    )
    rr.script_add_args(parser)
    args = parser.parse_args()

    blueprint = rrb.Blueprint(
        rrb.Grid(
            rrb.Spatial3DView(
                name='3D View',
                origin='/',
                contents=["+ /**"],
                spatial_information=rrb.SpatialInformation(
                    target_frame="gps",
                    show_axes=False,
                    show_bounding_box=False,
                ),
                eye_controls=rrb.EyeControls3D(
                    kind=rrb.Eye3DKind.FirstPerson,
                    position=(-2.51, -2.88, 0.55),
                    look_target=(0.0, 0.0, 0.0),
                    eye_up=(0.0, 0.0, 1.0),
                    speed=10.0,
                    spin_speed=0.0,
                ),
                background=rrb.Background(
                    kind=rrb.BackgroundKind.GradientBright,
                ),
            ),
            rrb.TextDocumentView(
                name='Description',
                contents='description',
            ),
            rrb.Spatial3DView(
                name='Top Down 3D View',
                origin='/',
                contents=["+ /**"],
                spatial_information=rrb.SpatialInformation(
                    target_frame="gps_fix_rot",
                    show_axes=False,
                    show_bounding_box=False,
                ),
                eye_controls=rrb.EyeControls3D(
                    kind=rrb.Eye3DKind.FirstPerson,
                    position=(0.0, 0.26, 36.38),
                    look_target=(0.0, 0.28, 35.38),
                    eye_up=(0.0, 0.0, 1.0),
                    speed=10.0,
                    spin_speed=0.0,
                ),
                background=rrb.Background(
                    kind=rrb.BackgroundKind.GradientBright,
                ),
            ),
            rrb.MapView(
                name='Map View',
                zoom=18,
            ),
        ),
        rrb.TimePanel(
            state=rrb.components.PanelState.Collapsed,
            play_state=rrb.components.PlayState.Playing,
            loop_mode=rrb.components.LoopMode.All,
        ),
        collapse_panels=False,
    )

    rr.script_setup(args, 'rerun_example_ros_tf', default_blueprint=blueprint)

    rr.send_blueprint(blueprint)

    rr.log(
        'description',
        rr.TextDocument(DESCRIPTION, media_type=rr.MediaType.MARKDOWN),
        static=True,
    )

    log_dataset(args.root_dir / args.dataset_file)

    rr.script_teardown(args)


if __name__ == "__main__":
    main()
