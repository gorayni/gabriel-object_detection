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

from base64 import b64encode
import cv2
import json
import multiprocessing
import numpy as np
import os
import pprint
import Queue
import socket
import struct
import sys
import time

import config
import cooking_cv as cc
import Task

sys.path.insert(0, "..")
import zhuocv as zc

if os.path.isdir("../../gabriel/server"):
    sys.path.insert(0, "../../gabriel/server")
import gabriel
import gabriel.proxy

LOG = gabriel.logging.getLogger(__name__)

config.setup(is_streaming=True)
display_list = config.DISPLAY_LIST

LOG_TAG = "Cooking Proxy: "


def reorder_objects(result):
    # build a mapping between faster-rcnn recognized object order to a standard order
    object_mapping = [-1] * len(config.LABELS)
    with open("model/labels.txt") as f:
        lines = f.readlines()
        for idx, line in enumerate(lines):
            line = line.strip()
            object_mapping[idx] = config.LABELS.index(line)

    for i in xrange(result.shape[0]):
        result[i, -1] = object_mapping[int(result[i, -1] + 0.1)]

    return result


def display_verbal_guidance(text):
    img_display = np.ones((200, 400, 3), dtype=np.uint8) * 100
    lines = text.split('.')
    y_pos = 30
    for line in lines:
        cv2.putText(img_display, line.strip(), (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.5, [0, 255, 0])
        y_pos += 50
    zc.check_and_display('text_guidance', img_display, display_list, resize_max=config.DISPLAY_MAX_PIXEL,
                         wait_time=config.DISPLAY_WAIT_TIME)


class CookingProxy(gabriel.proxy.CognitiveProcessThread):
    def __init__(self, image_queue, output_queue, engine_id, log_flag=True):
        super(CookingProxy, self).__init__(image_queue, output_queue, engine_id)
        self.log_flag = log_flag
        self.is_first_image = True

        # task initialization
        self.task = Task.Task()

        if config.PLAY_SOUND:
            ## for playing sound
            sound_server_addr = ("128.2.209.136", 4299)
            try:
                self.sound_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sound_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self.sound_sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                self.sound_sock.connect(sound_server_addr)
                LOG.info(LOG_TAG + "connected to sound playing server")
            except socket.error as e:
                LOG.warning(LOG_TAG + "Failed to connect to sound server at %s" % str(sound_server_addr))

    def terminate(self):
        super(CookingProxy, self).terminate()

    def handle(self, header, data):
        LOG.info("received new image")

        header['status'] = "nothing"
        result = {}  # default

        ## first image
        if self.is_first_image:
            self.is_first_image = False
            instruction = self.task.get_instruction(np.array([]))
            header['status'] = 'success'
            if instruction.get('speech', None) is not None:
                result['speech'] = instruction['speech']
                display_verbal_guidance(result['speech'])
                if config.PLAY_SOUND:
                    data = result['speech']
                    packet = struct.pack("!I%ds" % len(data), len(data), data)
                    self.sound_sock.sendall(packet)
            if instruction.get('image', None) is not None:
                feedback_image = b64encode(zc.cv_image2raw(instruction['image']))
                result['image'] = feedback_image
                zc.check_and_display('img_guidance', instruction['image'], display_list,
                                     resize_max=config.DISPLAY_MAX_PIXEL, wait_time=config.DISPLAY_WAIT_TIME)

            return json.dumps(result)

        ## preprocessing of input image
        img = zc.raw2cv_image(data)
        if header.get('holo_capture', None) is not None:
            zc.check_and_display('holo', img, display_list, resize_max=config.DISPLAY_MAX_PIXEL,
                                 wait_time=config.DISPLAY_WAIT_TIME)
            return json.dumps(result)
        zc.check_and_display('input', img, display_list, resize_max=config.DISPLAY_MAX_PIXEL,
                             wait_time=config.DISPLAY_WAIT_TIME)

        ## preprocessing of input image
        resize_ratio = 1
        if max(img.shape) > config.IMAGE_MAX_WH:
            resize_ratio = float(config.IMAGE_MAX_WH) / max(img.shape[0], img.shape[1])
            img = cv2.resize(img, (0, 0), fx=resize_ratio, fy=resize_ratio, interpolation=cv2.INTER_AREA)
        zc.check_and_display('input', img, display_list, resize_max=config.DISPLAY_MAX_PIXEL,
                             wait_time=config.DISPLAY_WAIT_TIME)

        ## get current state
        t = time.time()
        rtn_msg, objects_data = cc.process(img, resize_ratio, display_list)
        print time.time() - t

        ## for measurement, when the sysmbolic representation has been got
        if gabriel.Debug.TIME_MEASUREMENT:
            result[gabriel.Protocol_measurement.JSON_KEY_APP_SYMBOLIC_TIME] = time.time()

        # the object detection result format is, for each line: [x1, y1, x2, y2, confidence, cls_idx]
        objects = np.array(json.loads(objects_data))
        objects = reorder_objects(objects)
        if "object" in display_list:
            img_object = zc.vis_detections(img, objects, config.LABELS)
            zc.check_and_display("object", img_object, display_list, resize_max=config.DISPLAY_MAX_PIXEL,
                                 wait_time=config.DISPLAY_WAIT_TIME)
        LOG.info("object detection result: %s" % objects)

        ## for measurement, when the sysmbolic representation has been got
        if gabriel.Debug.TIME_MEASUREMENT:
            header[gabriel.Protocol_measurement.JSON_KEY_APP_SYMBOLIC_TIME] = time.time()

        ## get instruction based on state
        instruction = self.task.get_instruction(objects)
        if instruction['status'] != 'success':
            return json.dumps(result)
        header['status'] = 'success'
        if instruction.get('speech', None) is not None:
            result['speech'] = instruction['speech']
            display_verbal_guidance(result['speech'])
            if config.PLAY_SOUND:
                data = result['speech']
                packet = struct.pack("!I%ds" % len(data), len(data), data)
                self.sound_sock.sendall(packet)
        if instruction.get('image', None) is not None:
            feedback_image = b64encode(zc.cv_image2raw(instruction['image']))
            result['image'] = feedback_image
            zc.check_and_display('img_guidance', instruction['image'], display_list,
                                 resize_max=config.DISPLAY_MAX_PIXEL, wait_time=config.DISPLAY_WAIT_TIME)
        if instruction.get('holo_object', None) is not None:
            result['holo_object'] = instruction['holo_object']
        if instruction.get('holo_location', None) is not None:
            result['holo_location'] = instruction['holo_location']

        return json.dumps(result)


if __name__ == "__main__":
    settings = gabriel.util.process_command_line(sys.argv[1:])

    ip_addr, port = gabriel.network.get_registry_server_address(settings.address)
    service_list = gabriel.network.get_service_list(ip_addr, port)
    LOG.info("Gabriel Server :")
    LOG.info(pprint.pformat(service_list))

    video_ip = service_list.get(gabriel.ServiceMeta.VIDEO_TCP_STREAMING_IP)
    video_port = service_list.get(gabriel.ServiceMeta.VIDEO_TCP_STREAMING_PORT)
    ucomm_ip = service_list.get(gabriel.ServiceMeta.UCOMM_SERVER_IP)
    ucomm_port = service_list.get(gabriel.ServiceMeta.UCOMM_SERVER_PORT)

    # image receiving thread
    image_queue = Queue.Queue(gabriel.Const.APP_LEVEL_TOKEN_SIZE)
    print "TOKEN SIZE OF OFFLOADING ENGINE: %d" % gabriel.Const.APP_LEVEL_TOKEN_SIZE
    video_streaming = gabriel.proxy.SensorReceiveClient((video_ip, video_port), image_queue)
    video_streaming.start()
    video_streaming.isDaemon = True

    # app proxy
    result_queue = multiprocessing.Queue()

    app_proxy = CookingProxy(image_queue, result_queue, engine_id="Sandwich")
    app_proxy.start()
    app_proxy.isDaemon = True

    # result pub/sub
    result_pub = gabriel.proxy.ResultPublishClient((ucomm_ip, ucomm_port), result_queue)
    result_pub.start()
    result_pub.isDaemon = True

    try:
        while True:
            time.sleep(1)
    except Exception as e:
        pass
    except KeyboardInterrupt as e:
        sys.stdout.write("user exits\n")
    finally:
        if video_streaming is not None:
            video_streaming.terminate()
        if app_proxy is not None:
            app_proxy.terminate()
        result_pub.terminate()
