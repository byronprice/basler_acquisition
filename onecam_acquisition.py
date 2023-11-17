from pypylon import pylon
import numpy as np
from collections import deque
import traceback
import subprocess


class VideoWriter:
    def __init__(self, filename, fps, img_size):
        self.filename = filename
        self.fps = int(fps)
        self.img_size = img_size
        self.command = [
            'ffmpeg',
            '-y',  # Overwrite output file if it exists
            '-f', 'rawvideo',
            '-vcodec', 'rawvideo',
            '-s', f'{img_size[0]}x{img_size[1]}',
            '-pix_fmt', 'gray8',
            '-r', str(fps),
            '-i', '-',
            '-an',  # No audio
            '-vcodec', 'libx264',  # Use libx264 codec
            '-crf', '0',  # Set CRF to 0 for lossless
            filename
        ]
        self.process = subprocess.Popen(self.command, stdin=subprocess.PIPE)

    def write(self, frame):
        self.process.stdin.write(frame.tobytes())

    def release(self):
        self.process.stdin.close()
        self.process.wait()


class RecordBasler:
    def __init__(self, record_time = 600., filename = 'basler_video', frame_rate = 120., exposure_time = 8000., gain = 5.):
        self.record_time = record_time
        self.filename = filename+'.avi'
        self.fps = frame_rate
        self.exposure_time = exposure_time
        self.gain = gain

        tlf = pylon.TlFactory.GetInstance()
        camera = pylon.InstantCamera(tlf.CreateFirstDevice())
        self.camera = camera

        self.frame_queue = CreateQueue()

    def initialize_camera_and_video(self):
        # set up to output a pulse with each exposure
        self.camera.Open()
        self.camera.UserSetSelector = self.camera.UserSetDefault.Value
        self.camera.UserSetLoad.Execute()

        self.camera.Gain.Value = self.gain
        self.camera.ExposureTime.Value = self.exposure_time
        self.camera.AcquisitionFrameRateEnable = True
        self.camera.AcquisitionFrameRate.Value = self.fps
        self.camera.LineSelector = 'Line2'
        self.camera.LineMode = 'Output'
        self.camera.LineMinimumOutputPulseWidth.Value = 100
        self.camera.LineSource = 'ExposureActive'

        # initialize video writer
        frame_width = int(self.camera.Width.Value)
        frame_height = int(self.camera.Height.Value)

        img_size = (frame_width, frame_height)
        self.video_writer = VideoWriter(self.filename, self.fps, img_size)

        print('Camera and Video Writer Initialized ...')

    def acquire_video(self):

        num_images = int(self.fps * self.record_time)
        # self.camera.StartGrabbingMax(numberOfImagesToGrab)

        print('\nRecording set to run for', self.record_time,'seconds')
        handler = ImageHandler(self.frame_queue)
        self.camera.RegisterImageEventHandler(handler, pylon.RegistrationMode_ReplaceAll, pylon.Cleanup_None)

        self.camera.StartGrabbingMax(num_images, pylon.GrabStrategy_OneByOne, pylon.GrabLoop_ProvidedByInstantCamera)

        while self.camera.IsGrabbing(): # write video to .avi
            if bool(self.frame_queue):
                self.video_writer.write(self.frame_queue.dequeue()) 

        print(len(self.frame_queue))
        # continue removing items from the queue
        while bool(self.frame_queue):
            self.video_writer.write(self.frame_queue.dequeue())

        self.camera.StopGrabbing()
        self.camera.DeregisterImageEventHandler(handler)

        self.camera.Close()

        self.video_writer.release()

        print('Recording completed successfully')


class ImageHandler(pylon.ImageEventHandler):
    def __init__(self, frame_queue):
        super().__init__()
        self.frame_queue = frame_queue

    def OnImageGrabbed(self, camera, grabResult):
        """ we get called on every image
            !! this code is run in a pylon thread context
            always wrap your code in the try .. except to capture
            errors inside the grabbing as this can't be properly reported from
            the background thread to the foreground python code
        """
        try:
            if grabResult.GrabSucceeded():
                # add image to queue
                # img = grabResult.Array
                self.frame_queue.enqueue(grabResult.Array)
            else:
                raise RuntimeError("Grab Failed")
        except Exception as e:
            traceback.print_exc()


class CreateQueue:
    """
    A simple implementation of a FIFO queue.
    """

    def __init__(self):
        """
        Initialize the queue.
        """
        self._items = deque()

    def __len__(self):
        """
        Return the number of items in the queue.
        """
        return len(self._items)

    def __bool__(self):
        """
         returns True if queue is not empty
        """
        return len(self._items) > 0

    def __iter__(self):
        """
        Create an iterator for the queue.
        """
        for item in self._items:
            yield item

    def __str__(self):
        """
        Return a string representation of the queue.
        """
        items = []
        for item in self:
            items.append(item)

        return str(items)

    def __contains__(self, item):
        """
         check if item is contained in queue
        """

        return item in self._items

    def enqueue(self, item):
        """
        Add item to the queue.
        """
        self._items.append(item)

    def dequeue(self):
        """
        Remove and return the least recently inserted item.
        """
        if self:
            return self._items.popleft()

    def clear(self):
        """
        Remove all items from the queue.
        """
        self._items = deque()
