'''
--- This is version 9.3 ---

    Resolved the issue of camera conflict while stopping capture threads.
    The problem was: When two capture threads use the same camera...
        and when one of the threads closes its own camera, the other thread is still using the same camera...
        therefore causing errors.

    The approach to resolve the conflict issue is by drawing camera objects up to a higher level.
    I instantiated all cameras in the windu_model.

    When stopping video, stop all capture threads before closing any camera.



--- Version 9.2 ---

    Create the class AbstractThread as the superclass of all threads.

    The AbstractThread standardize runtime controls including start(), stop(), resume() and pause()...
        as well as frame rate (fps) of the main loop.

    This abstraction makes all threads become lighter and more focused on its own specific task...
        reducing the hefty codes for runtime control.



--- Version 9.1 ---

    Extract the VideoWriter from the process thread...
        and make it as an independent writer thread.

    The writer thread needs to use the active process thread...
        to record current displayed images in the video file.



--- Version 9.0 ---

    From version 8.6 to 9.0 is a major overhaul.

    On the surface the codes have been spread out to more files.

    I attempted to add the third ambient (or extra) camera and...
        the capture thread became too slow...
        because three cameras were operated in a single loop.

    Therefore I created 3 seperate capturing threads named with constants CAM_R, CAM_L, CAM_E,
        each operating a single cv2.VideoCapture camera.

    By spawning 3 capturing threads, the runtime of 3 cameras have been completely decoupled.

    Because there are 2 viewing modes - MICRO and ANBIENT - I created 2 processing threads...
        for 2 different viewing modes.

    The MICRO processing thread uses 2 capturing threads - CAM_R and CAM_L - for two eyes.

    The AMBIENT processing thread uses 1 capturing thread - CAM_E - for both eyes.

    The 3 capturing threads runs concurrently, so the 3 cameras are just constantly working.

    The 2 processing threads are mutually exclusive, meaning that only one of them...
        actively runs at any given moment, while the other is paused.

    The 2 processing threads are basically "state pattern".
    Both of them have identical set of methods like zoom_in, zoom_out... etc.



--- Version 8.6 ---

    Automatic camera (right) tuning for correct lighting:

        (1) Set default brightness, contrast and gain
        (2) Adjust exposure until the image lighting is the closest to the goal (usually 128)
        (3) Adjust gain until the difference (between image lighting and goal) < 1



--- Version 8.5 ---

    Fixed the bug when switching to full screen by...
        changing the image dimension of imgR_proc and imgL_proc in the ProcessThread class



--- Version 8.4 ---

    Time the main loop in the ProcessThread class.

    The timing goes down to the level of milliseconds, which makes it less reliable across platforms...
        especially in Windows.



--- Version 8.3 ---

    Major structural changes in the Model.

    Split the VideoThread class into two classes:

        CaptureThread: A thread that possesses the dual camera and ONLY captures images on runtime.

        ProcessThread: A thread that fetches images from the CaptureThread, process and display it to gui.

    By this split, I am completely decoupling image capturing and image processing. Hence both
    capturing and processing can run at full speed simultaneously. Since it runs faster, it is
    possible to TIME the image processing (and display) loop at an fps >= 30.

    With a steadily timed frame rate, the cv2.VideoWriter in the ProcessThread can record at a
    correct frame rate.

    There were a lot of code refactoring, but the methods in the old VideoThread were pretty much
    ditributed in the two new classes - CaptureThread and ProcessThread - unchanged.



--- Version 8.2 ---

    Introduced file saving dialog for snapshot and video recording.



--- Version 8.1 ---

    Downloaded the compressive X264 codec and it works!
    The recorded video file size is minute compared to uncompressive codecs like I420.



--- Version 8.0 ---

    In version 8.X shift the focus to video recording.

    In this version figure out the fourcc codec for cv2.VideoWriter object.

    Before I just put fourcc = -1, and there was a pop-up menu at runtime for selecting codec.
    When the source code is compiled into executable, this pop-up menu does not happen.
    Without a proper codec the VideoWriter does not work.

    After figuring out the fourcc codec, not the executable version can record video.



--- Version 7.7 ---

    Some minor modifications:

    Introduce limits (50, 50) to image offset in the VideoThread class.

    Put toggle_auto_offset in developer mode. Automatically turn it on when initiating software.



--- Version 7.6 ---

    Restructured the main loop of the CamEqualThread class:
        Factor out gain adjustment to a seperate method self.adjust_gain(iter)



--- Version 7.5 ---

    (1) Fix the bug of copying right camera id to the left camera id
        in the CamEqualThread class.

    (2) Change the camera gain range to 0-127.

    (3) In CameraTunerWindow class change the interval of parameters.



--- Version 7.4 ---

    (1) Copy the right camera parameter to the left camera
        before resuming the camera equalization process.

    (2) Fixing the problem of camera equalization not converging (infinite loop),
        by limiting the number of iteration.



--- Version 7.3 ---

    Change the runtime behavior of CamEqualThread.

    Make the CamEqualThread a continuous thread running concurrently with the VideoThread.
    Triggering camera equalization is by resuming the loop in self.run().
    With this behavior, the runtime status can be switched between paused and un-paused.

    Reason for making a continuously running thread:
        Before I instantiate a CamEqualThread object every time needed.
        This could cause runtime problem when the user triggers the instantiation of a new
        thread object before the previous one is done.



--- Version 7.2 ---

    Refactor and unify the interface of camera parameters:

    (1) Replace isRightCam=True/False with side='L'/'R'.

    (2) Writing of the file cam.json is placed in DualCam object,
        so that the cam.json file is always bound to the current status of the camera.

    (3) Always get/set parameters of only one camera at a time.

    (4) Modify the CameraTunerWindow class and its parent classes, so that
        each time the window is opened, camera parameters is loaded from the cam.json file.



--- Version 7.1 ---

    Introduced automatic camera tuning.

    In this first version for camera tuning,
        adjust left camera gain to equalize brightness levels in both images.

    Create a CamEqualThread class which operates via the VideoThread object:
        (1) Access and analyze images
        (2) Control camera gains



--- Version 7.0 ---

    Major change from 6.4 to 7.0:
        Split one set of camera parameters into two sets for right and left cameras, respective.
        This entails an extensive change of code strucutures and interfaces.
        Conceptually, everything involving camera parameters (get, set, read, write) is duplicated.
        The GUI window for setting camera parameters is also duplicated.

    Here I list the most notable changes:

    (1) Data structure of the 'cam.json' file, i.e. the camera parameters:
        {'R': {dictionary of parameters}, 'L': {dictionary of parameters}}

    (2) Extensive changes in the CameraTunerWindow class to account for right or left.

    (3) Instantiate two camera tuner windows, for R and L, respectively, in the main WinduGUI object.
        Related methods like open_camera_tuner() is also modified.

    (4) The data transferred from a CameraTunerWindow object to the WinduCore object is changed to the structure of
        {'isRightCam': True/False, 'parameters': {dictionary of parameters}}.

    (5) Changes in the apply_camera_parameters() methods in WinduCore, VideoThread classes.

    (6) Extensive changes in the DualCamera class.
        DualCamera class is a low-leveled class that directly operates camera hardwares (VideoCapture objects).
        The two VideoCapture objects are configured separately.



--- Version 6.4 ---

    Abandone the auto_offset() method, which aligns the left image to the right image for only one shot.

    For GUI control, replace the auto_offset() method with toggle_auto_offset().
    This toggling method pauses/resumes the loop in the AlignThread.
    Therefore users can turn ON or OFF the continuous alignment function.

    The main loop in the AlignThread was modified for pausing/resuming.

    The GUI icons for the toggle_auto_offset() method was also changed.
    Users can see the status, either ON or OFF, of auto offset.



--- Version 6.3 ---

    Major changes has been done in the AlignThread class,
    to resolve the problem of "jumping" image when there is a active and quick movement under the microscope.

    This jumping problem is possibly caused by asynchronous imaging of the two cameras, and
    can be considered as an outlier of alignment offset.

    Approaches to resolve the jumpiness:

        (1) Construct a queue of the past 10 offset values.
            Sort them, take out the highest and the lowest values.
            Average the median values.

        (2) Use the averaged values to set image offset.

        (3) If the current offset value differs significantly from the average, meaning that there is more "active movements",
            then speed up the loop to get back to a stable condition as soon as possible.



--- Version 6.2 ---

    Restructured the image processing pipeline in the video_thread object, with a few major points:

        (1) Combine the offset matrix and resize matrix into one single transformation matrix.

            This makes the image processing more efficient because the offset operation is
            combined into the resize operation.

            For mathematical details see 'transformation_matrix.docx'.

        (2) Factor out the depth computation into a separate method.

            Depth computation is done on the scaled images.



--- Version 6.1 ---

    Auto offset is executed upon inititating the software,
    which includes both vertical and horizontal offsets.

    There is a concurrent thread 'align_thread' running with the video_thread.
    The align_thread executes ONLY the vertical alignment every ~1 second.
    The horizontal offset should NOT be changed frequently to avoid visual discomfort.

'''

if __name__ == '__main__':
    from windu_model import *
    app = QtGui.QApplication(sys.argv)
    core = WinduCore()
    sys.exit(app.exec_())
