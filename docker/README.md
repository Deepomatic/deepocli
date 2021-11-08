# Build the docker image

```bash
$ docker build -t opencv-python .
```

# Run the container

```bash
$ docker run -it opencv-python bash
# Check installation
pip3 install deepomatic-cli
deepo platform model draw -i $input_video -o $output_video -r $recognition_id --fourcc avc1
```

# Get the wheel package and install it on another computer

```bash
opencv_version=3.4.16.57
id=$(docker create opencv-python)
docker cp $id:/tmp/build/opencv-python/opencv_contrib_python_headless-$opencv_version-cp38-cp38-linux_x86_64.whl .
docker rm -v $id
```

Then you can run `pip3 install opencv_contrib_python_headless-*.whl` on the host.


# Responsability

You are responsible for any legal considerations regarding the use of H264 encoder.
https://www.ffmpeg.org/legal.html
https://web.archive.org/web/20050524073352/http://www.mpegla.com/news/n_03-11-17_avc.html
