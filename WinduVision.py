'''
--- This is version 6.3 ---

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
    from WinduModel import *
    app = QtGui.QApplication(sys.argv)
    core = WinduCore()
    sys.exit(app.exec_())
