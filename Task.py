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

import cv2
import math
import xml.etree.ElementTree as ET

import config

OBJECTS = config.LABELS  # ["bread", "ham", "cucumber", "lettuce", "cheese", "half", "hamwrong", "tomato", "full"]
STATES = ["start", "nothing", "bread", "ham", "lettuce", "cucumber", "half", "tomato", "hamwrong", "full"]


class Task:
    def __init__(self):
        tree = ET.parse("recipe.xml")
        root = tree.getroot()
        instructions = root.find('instructions')
        self.instructions = {}
        for instruction in instructions:
            state = instruction.get('state')
            speech = instruction.find('speech').text.strip()
            image_path = instruction.find('image').get('path')
            image = cv2.imread(image_path) if image_path else None
            self.instructions[state] = {'speech': speech, 'image': image}

        self.current_state = "start"

    def _get_holo_location(self, objects, label_idx=-1, pos_paras=[5000, 0.5, 0.5]):
        dist_para, x_para, y_para = pos_paras
        objects = objects[objects[:, -1] == label_idx, :]
        x1, y1, x2, y2 = objects[0, :4]
        x = x1 * (1 - x_para) + x2 * x_para
        y = y1 * (1 - y_para) + y2 * y_para
        area = (y2 - y1) * (x2 - x1)
        return {'x': x, 'y': y, 'depth': math.sqrt(dist_para / float(area))}

    def get_instruction(self, objects):
        # @objects format: [x1, y1, x2, y2, confidence, cls_idx]

        result = {'status': "nothing"}

        # the start
        if self.current_state == "start":
            result = self.instructions['nothing']
            result['status'] = "success"
            self.current_state = "nothing"
            return result

        if len(objects.shape) < 2:  # nothing detected
            return result

        # get the count of detected objects
        object_counts = []
        for i in xrange(len(OBJECTS)):
            object_counts.append(sum(objects[:, -1] == i))

        if self.current_state == "nothing":
            if object_counts[0] > 0:
                result = self.instructions['bread']
                result['status'] = "success"
                result['holo_object'] = "ham"
                result['holo_location'] = self._get_holo_location(objects, label_idx=0,
                                                                  pos_paras=config.holo_pos_paras['ham'])
                self.current_state = "bread"

        elif self.current_state == "bread":
            if object_counts[1] > 0:
                result = self.instructions['ham']
                result['status'] = "success"
                result['holo_object'] = "lettuce"
                result['holo_location'] = self._get_holo_location(objects, label_idx=1,
                                                                  pos_paras=config.holo_pos_paras['lettuce'])
                self.current_state = "ham"
            elif object_counts[0] > 0:
                result['status'] = "success"
                result['holo_object'] = "ham"
                result['holo_location'] = self._get_holo_location(objects, label_idx=0,
                                                                  pos_paras=config.holo_pos_paras['ham'])

        elif self.current_state == "ham":
            if object_counts[3] > 0:
                result = self.instructions['lettuce']
                result['status'] = "success"
                result['holo_object'] = "bread"
                result['holo_location'] = self._get_holo_location(objects, label_idx=3,
                                                                  pos_paras=config.holo_pos_paras['bread'])
                self.current_state = "lettuce"
            elif object_counts[2] > 0:
                result = self.instructions['cucumber']
                result['status'] = "success"
                self.current_state = "cucumber"
            elif object_counts[0] > 0 and object_counts[1] == 0:
                result = self.instructions['bread']
                result['status'] = "success"
                result['holo_object'] = "ham"
                result['holo_location'] = self._get_holo_location(objects, label_idx=0,
                                                                  pos_paras=config.holo_pos_paras['ham'])
                self.current_state = "bread"
            elif object_counts[1] > 0:
                result['status'] = "success"
                result['holo_object'] = "lettuce"
                result['holo_location'] = self._get_holo_location(objects, label_idx=1,
                                                                  pos_paras=config.holo_pos_paras['lettuce'])

        elif self.current_state == "lettuce":
            if object_counts[5] > 0:
                result = self.instructions['half']
                result['status'] = "success"
                result['holo_object'] = "tomato"
                result['holo_location'] = self._get_holo_location(objects, label_idx=5,
                                                                  pos_paras=config.holo_pos_paras['tomato'])
                self.current_state = "half"
            elif object_counts[1] > 0 and object_counts[3] == 0:
                result = self.instructions['ham']
                result['status'] = "success"
                result['holo_object'] = "lettuce"
                result['holo_location'] = self._get_holo_location(objects, label_idx=1,
                                                                  pos_paras=config.holo_pos_paras['lettuce'])
                self.current_state = "ham"
            elif object_counts[3] > 0:
                result['status'] = "success"
                result['holo_object'] = "bread"
                result['holo_location'] = self._get_holo_location(objects, label_idx=3,
                                                                  pos_paras=config.holo_pos_paras['bread'])

        elif self.current_state == "cucumber":
            if object_counts[3] > 0:
                result = self.instructions['lettuce']
                result['status'] = "success"
                self.current_state = "lettuce"
            elif object_counts[1] > 0 and object_counts[3] == 0:
                result = self.instructions['ham']
                result['status'] = "success"
                result['holo_object'] = "lettuce"
                result['holo_location'] = self._get_holo_location(objects, label_idx=1,
                                                                  pos_paras=config.holo_pos_paras['lettuce'])
                self.current_state = "ham"

        elif self.current_state == "half":
            if object_counts[7] > 0:
                result = self.instructions['tomato']
                result['status'] = "success"
                result['holo_object'] = "breadtop"
                result['holo_location'] = self._get_holo_location(objects, label_idx=7,
                                                                  pos_paras=config.holo_pos_paras['breadtop'])
                self.current_state = "tomato"
            elif object_counts[6] > 0:
                result = self.instructions['hamwrong']
                result['status'] = "success"
                self.current_state = "hamwrong"
            elif object_counts[3] > 0 and object_counts[5] == 0:
                result = self.instructions['lettuce']
                result['status'] = "success"
                result['holo_object'] = "bread"
                result['holo_location'] = self._get_holo_location(objects, label_idx=3,
                                                                  pos_paras=config.holo_pos_paras['bread'])
                self.current_state = "lettuce"
            elif object_counts[5] > 0:
                result['status'] = "success"
                result['holo_object'] = "tomato"
                result['holo_location'] = self._get_holo_location(objects, label_idx=5,
                                                                  pos_paras=config.holo_pos_paras['tomato'])

        elif self.current_state == "tomato":
            if object_counts[8] > 0:
                result = self.instructions['full']
                result['status'] = "success"
                result['holo_object'] = "none"
                result['holo_location'] = {}
                self.current_state = "full"
            elif object_counts[5] > 0 and object_counts[7] == 0:
                result = self.instructions['half']
                result['status'] = "success"
                result['holo_object'] = "tomato"
                result['holo_location'] = self._get_holo_location(objects, label_idx=5,
                                                                  pos_paras=config.holo_pos_paras['tomato'])
                self.current_state = "half"
            elif object_counts[7] > 0:
                result['status'] = "success"
                result['holo_object'] = "breadtop"
                result['holo_location'] = self._get_holo_location(objects, label_idx=7,
                                                                  pos_paras=config.holo_pos_paras['breadtop'])

        elif self.current_state == "hamwrong":
            if object_counts[7] > 0:
                result = self.instructions['tomato']
                result['status'] = "success"
                result['holo_object'] = "breadtop"
                result['holo_location'] = self._get_holo_location(objects, label_idx=7,
                                                                  pos_paras=config.holo_pos_paras['breadtop'])
                self.current_state = "tomato"
            elif object_counts[5] > 0 and object_counts[7] == 0:
                result = self.instructions['half']
                result['status'] = "success"
                result['holo_object'] = "tomato"
                result['holo_location'] = self._get_holo_location(objects, label_idx=5,
                                                                  pos_paras=config.holo_pos_paras['tomato'])
                self.current_state = "half"

        return result
