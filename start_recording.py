from sys import argv
from onecam_acquisition import *

if len(argv) == 1:
    record_obj = RecordBasler()
elif len(argv) == 2:
    total_time = float(argv[1])
    record_obj = RecordBasler(total_time)
elif len(argv) == 3:
    total_time = float(argv[1])
    output_file = str(argv[2])
    record_obj = RecordBasler(total_time, output_file)
elif len(argv) == 4:
    total_time = float(argv[1])
    output_file = str(argv[2])
    frames_per_second = float(argv[3])
    record_obj = RecordBasler(total_time, output_file, frames_per_second)


# initialize camera and video writer
record_obj.initialize_camera_and_video()

# start acquiring video
record_obj.acquire_video()
