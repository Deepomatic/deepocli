# coding: utf-8
import os
import json
import tempfile
import requests

def download(tmpdir, url, filepath):
	path = os.path.join(tmpdir, filepath)
	if not os.path.isdir(os.path.dirname(path)):
		os.makedirs(os.path.dirname(path))
	r = requests.get(url)
	with open(path, 'wb') as f:
		f.write(r.content)
	return path

def init_files_setup():
	"""
	Download all files for the tests. The files structure is the following

	tmpdir
	├── img_dir
	│   ├── img1.jpg
	│   ├── img2.jpg
	│   └── subdir
	│       └── img3.jpg
	├── single_img.jpg
	├── studio.json
	└── video.mp4
	"""
	# Download all fies
	tmpdir = tempfile.mkdtemp()
	single_img_pth = download(tmpdir, 'https://s3-eu-west-1.amazonaws.com/deepo-tests/vulcain/images/test.jpg', 'single_img.jpg')
	video_pth = download(tmpdir, 'https://s3-eu-west-1.amazonaws.com/deepo-tests/vulcain/images/test.mp4', 'video.mp4')
	img1_pth = download(tmpdir, 'https://s3-eu-west-1.amazonaws.com/deepo-tests/vulcain/images/test.jpg', 'img_dir/img1.jpg')
	img2_pth = download(tmpdir, 'https://s3-eu-west-1.amazonaws.com/deepo-tests/vulcain/images/test.jpg', 'img_dir/img2.jpg')
	img3_pth = download(tmpdir, 'https://s3-eu-west-1.amazonaws.com/deepo-tests/vulcain/images/test.jpg', 'img_dir/subdir/img3.jpg')
	json_pth = download(tmpdir, 'https://s3-eu-west-1.amazonaws.com/deepo-tests/vulcain/json/studio.json', 'studio.json')
	img_dir_pth = os.path.dirname(img1_pth)

	# Update json for path to match
	with open(json_pth, 'r') as json_file:
		json_data = json.load(json_file)
	json_data['images'][0]['location'] = single_img_pth
	with open(json_pth, 'w') as json_file:
		json.dump(json_data, json_file)

	return single_img_pth, video_pth, img_dir_pth, json_pth, tmpdir

if __name__ == '__main__':
	init_files_setup()