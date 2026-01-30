#!/usr/bin/env python3
from __future__ import annotations

import rerun as rr

import argparse

from datafusion import col
import pyarrow as pa

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Retrieve RRD TF info.")
    parser.add_argument(
        'PATH_TO_INPUT_RRDS',
        nargs='*',
        help='Paths to read from. Reads from standard input if none are specified'
    )
    parser.add_argument(
        '--remove-leading-slash',
        action='store_true',
        help='Remove leading slash from frame names'
    )
    args = parser.parse_args()

    with rr.server.Server(datasets={"tf_info_dataset": args.PATH_TO_INPUT_RRDS}) as server:
        dataset = server.client().get_dataset(name="tf_info_dataset")

        entity = '/tf'
        child_frame_col = f'{entity}:Transform3D:child_frame'
        parent_frame_col = f'{entity}:Transform3D:parent_frame'
        timeline = 'ros2_timestamp'

        df = dataset.filter_contents([entity]).reader(index=timeline)

        child_frame = pa.table(df.select(col(child_frame_col)[0]))[0].to_pylist()
        parent_frame = pa.table(df.select(col(parent_frame_col)[0]))[0].to_pylist()

        if args.remove_leading_slash:
            child_frame = [frame[1:] if frame.startswith(
                '/') else frame for frame in child_frame]
            parent_frame = [frame[1:] if frame.startswith(
                '/') else frame for frame in parent_frame]

        frames = sorted(list(set(zip(parent_frame, child_frame))))
        print("Parent Frame → Child Frame:")
        print("──────────────────────────")
        for frame in frames:
            print(f'{frame[0]} → {frame[1]}')


if __name__ == "__main__":
    main()