#!/usr/bin/env python
#
# Cloudlet Infrastructure for Mobile Computing
#   - Task Assistance
#
#   Author: Zhuo Chen <zhuoc@cs.cmu.edu>
#
#   Copyright (C) 2011-2013 Carnegie Mellon University
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#

'''
This is a simple library file for common CV tasks
'''

import cv2
import numpy as np
import os
import sys


def cv_image2raw(img, jpeg_quality=95):
    result, data = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, jpeg_quality])
    raw_data = data.tostring()
    return raw_data


def raw2cv_image(raw_data, gray_scale=False):
    img_array = np.asarray(bytearray(raw_data), dtype=np.int8)
    color = 0 if gray_scale else -1
    return cv2.imdecode(img_array, color)


def display_image(display_name, img, wait_time=-1, is_resize=True, resize_method="max", resize_max=-1, resize_scale=1,
                  save_image=False):
    '''
    Display image at appropriate size. There are two ways to specify the size:
    1. If resize_max is greater than zero, the longer edge (either width or height) of the image is set to this value
    2. If resize_scale is greater than zero, the image is scaled by this factor
    '''
    if is_resize:
        img_shape = img.shape
        height = img_shape[0];
        width = img_shape[1]
        if resize_max > 0:
            if height > width:
                img_display = cv2.resize(img, (resize_max * width / height, resize_max),
                                         interpolation=cv2.INTER_NEAREST)
            else:
                img_display = cv2.resize(img, (resize_max, resize_max * height / width),
                                         interpolation=cv2.INTER_NEAREST)
        elif resize_scale > 0:
            img_display = cv2.resize(img, (width * resize_scale, height * resize_scale),
                                     interpolation=cv2.INTER_NEAREST)
        else:
            print "Unexpected parameter in image display. About to exit..."
            sys.exit()
    else:
        img_display = img

    cv2.imshow(display_name, img_display)
    cv2.waitKey(wait_time)
    # if save_image:
    if True:
        if not os.path.isdir('tmp'):
            os.mkdir('tmp')
        file_path = os.path.join('tmp', display_name + '.png')
        cv2.imwrite(file_path, img_display)


def check_and_display(display_name, img, display_list, wait_time=-1, is_resize=True, resize_method="max", resize_max=-1,
                      resize_scale=1, save_image=False):
    if display_name in display_list:
        display_image(display_name, img, wait_time, is_resize, resize_method, resize_max, resize_scale, save_image)


def vis_detections(img, dets, labels, thresh=0.5):
    # dets format should be: [x1, y1, x2, y2, confidence, cls_idx]
    if len(dets.shape) < 2:
        return img
    inds = np.where(dets[:, -2] >= thresh)[0]

    img_detections = img.copy()
    if len(inds) > 0:
        for i in inds:
            cls_name = labels[int(dets[i, -1] + 0.1)]
            bbox = dets[i, :4]
            score = dets[i, -2]
            text = "%s : %f" % (cls_name, score)
            # print 'Detected roi for %s:%s score:%f' % (cls_name, bbox, score)
            cv2.rectangle(img_detections, (int(bbox[0]), int(bbox[1])), (int(bbox[2]), int(bbox[3])), (0, 0, 255), 8)
            cv2.putText(img_detections, text, (int(bbox[0]), int(bbox[1])), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
    return img_detections
