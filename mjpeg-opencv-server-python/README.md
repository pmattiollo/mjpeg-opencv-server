# mjpg-opencv-server-python Project

## Functionality

This project is a demo of OpenCV reading a remote MJPG stream, applying processing and outputting result as another MJPG stream.

### Points of interest:

- [main.py](main.py) - http server that returns MJPG stream with OpenCV-processed images. Includes a demo of face detection algorithm being applied.

Specify the correct URL to your remote MJPG stream in `REMOTE_MJPEG_URL` variable in main.py file.

## Prerequisites

> ⚠️ It is recommended to use virtual environments with Python https://docs.python.org/3/tutorial/venv.html

This project uses several dependencies listed in the [requirements.txt](requirements.txt)

To install dependencies, run the following command:

```shell
pip install -r requirements.txt
```

## Running the application

To run the application, run `main.py`:

```shell
python3 main.py
```

## Dependencies

- [OpenCV](https://pypi.org/project/opencv-python/) - computer vision and image processing
- [Pillow](https://pillow.readthedocs.io/en/stable/) - image conversion
