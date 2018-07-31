#!/usr/bin/env python
import argparse
import glob
import os
import shutil
import sys

def add_preceding_zeros(n, total_length = 5):
    if n < 10:
        return "0" * (total_length - 1) + str(n)
    elif n < 100:
        return "0" * (total_length - 2) + str(n)
    elif n < 1000:
        return "0" * (total_length - 3) + str(n)
    elif n < 10000:
        return "0" * (total_length - 4) + str(n)
    elif n < 100000:
        return "0" * (total_length - 5) + str(n)
    elif n < 1000000:
        return "0" * (total_length - 6) + str(n)

def main():
    input_folder, output_folder, shift_size = parse_arguments()
    if not os.path.isdir(output_folder):
        os.mkdir(output_folder)
    for img_path in sorted(glob.glob(os.path.join(input_folder, '*'))):
        input_folder_abspath, file_name = img_path.rsplit('/')
        output_folder_abspath = input_folder_abspath.replace(input_folder, output_folder)
        suffix = file_name.rsplit('.')[1]
        prefix = file_name.split('-')[0]
        number_str = file_name.split('-')[1].rsplit('.')[0]
        number = int(number_str)
        number += shift_size
        if number <= 0:
            continue
        number_str = add_preceding_zeros(number)
        file_name_new = prefix + '-' + number_str + '.' + suffix
        img_path_new = os.path.join(output_folder_abspath, file_name_new)

        print img_path, img_path_new
        shutil.copyfile(img_path, img_path_new)


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input_folder",
                        default = "experiment_combine",
                        help = "The input folder containing images.",
                        )
    parser.add_argument("-o", "--output_folder",
                        default = "experiment_combine_new",
                        help = "The output folder.",
                        )
    parser.add_argument("-s", "--shift_size",
                        default = "shift_size", type = int,
                        help = "The number to shift.",
                        )
    args = parser.parse_args()

    return (args.input_folder, args.output_folder, args.shift_size)

if __name__ == '__main__':
    main()
