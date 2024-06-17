import argparse
import glob
import logging
import os
import re
from PIL import Image

from remove_unused_figures import get_disk_use
from utils import get_image_refs_of_line, get_absolute_img_path


def parse_args_to_dict():

    parser = argparse.ArgumentParser(
        description="Clean the .tex file a bit for better conversion to markdown with Pandoc."
    )
    parser.add_argument(
        "-i",
        "--input-folder",
        type=str,
        required=True,
        default="/home/petteri/Dropbox/KnowledgeBase",
        help="Where is / are your .tex files located?",
    )
    args_dict = vars(parser.parse_args())

    return args_dict


def get_all_img_files(input_folder):

    ext = ['*.png', '*.jpg', '*.jpeg', '*.gif', '*.svg']
    if isinstance(ext, list):
        files = []
        for e in ext:
            files_e = glob.glob(os.path.join(input_folder, '**', e), recursive=True)
            files += files_e
        files = sorted(files)
        logging.info(f"Found {len(files)} (multiple extensions: {ext}) files from {input_folder}")
    else:
        files = glob.glob(os.path.join(input_folder, '**', ext), recursive=True)
        logging.info(f"Found {len(files)} {ext} files from {input_folder}")

    # replace whitespace with %20 in the listing
    files_out = []
    for file in files:
        files_out.append(file.replace(' ', '%20'))

    return files_out

def process_md_files_for_optimization(input_folder, export_on = True):

    img_files = get_all_img_files(input_folder)
    md_files = sorted(glob.glob(os.path.join(input_folder, '**', '*.md'), recursive=True))
    for i, md_file in enumerate(md_files):

        logging.info(f"Processing {i+1}/{len(md_files)}: {md_file}")
        with open(md_file, 'r') as f:
            lines = f.readlines()

        if 'Computational Art' in md_file:
            print('debug')

        lines_out, lines_changed = optimize_imgs_references(lines, img_files)

        if export_on:
            if len(lines_changed) > 0:
                os.rename(md_file, md_file + '.bakMDupp')
                with open(md_file, 'w') as f:
                    f.writelines(lines_out)

        logging.info(f"->  {len(lines_changed)} lines changed images.")

    img_files_out = get_all_img_files(input_folder)
    img_size_out, not_found = get_disk_use(img_files_out)


def optimize_imgs_references(lines, img_files):

    lines_changed = []
    lines_out = []
    for i, line in enumerate(lines):
        if '![' in line:
            line, image_path_out = process_line_for_img_optimization(line, img_files)
            if image_path_out is not None:
                lines_changed.append((i, line, image_path_out))
        lines_out.append(line)

    return lines_out, lines_changed


def decide_whether_to_convert(image_path):

    basename = os.path.basename(image_path)
    fname, ext = os.path.splitext(basename)

    convert_ON = False
    if 'png' in ext:

        image_path = image_path.replace('%20', ' ')
        if not os.path.exists(image_path):
            logging.warning(f"Image {image_path} does not exist. Cannot convert it.")
            return convert_ON
        else:
            # TODO! You could do some quick'n'dirty FFT here for tables and such, with
            #  high spatial frequencies indicating that the image is not a photo, and you
            #  would like to keep it as a vector graphic instead of converting to JPEG
            convert_ON = True
            return convert_ON

    return convert_ON


def process_single_img_name(image_path, ext = 'jpg'):

    image_path = image_path.replace('%20', ' ')
    if os.path.exists(image_path):
        file_stats = os.stat(image_path)
        size_in_kB = file_stats.st_size / (1024)
        fname, extension_in = os.path.splitext(image_path)
        if extension_in == '.png':
            new_img_name = f"{fname}.{ext}"
        else:
            new_img_name = None
    else:
        logging.warning(f"Image {image_path} does not exist. Cannot convert it.")
        return None

    return new_img_name


def get_out_ref(ref, image_path_out):

    fname_out = os.path.basename(image_path_out)
    ref_out = fname_out

    return ref_out


def convert_image(image_path, image_path_out):

    image_path = image_path.replace('%20', ' ')
    # NOTE! This now requires that your attachment names are unique, which you can achieve e.g. with:
    # https://github.com/dy-sh/obsidian-unique-attachments or run the "uniquenize_img_names_and_move.py" script

    if not os.path.exists(image_path_out):
        # TODO! Does not handle yet unique names no matter what the extension is
        #  e.g. you could have image44.png and image44.jpg, and converting the .png to .jpg would overwrite the .jpg

        if os.path.exists(image_path):
            size_in_kB = os.stat(image_path).st_size / (1024)
            img = Image.open(image_path)
            img = img.convert('RGB')
            img.save(image_path_out, format='JPEG', subsampling=0, quality=85)  # Save the image
            size_out_kB = os.stat(image_path_out).st_size / (1024)

            # if size_out_kB > size_in_kB:
            #     # no point in converting to a larger file size with lossy compression
            #     logging.debug(f"Image {image_path} was not converted to {image_path_out} because it would have been larger.")
            #     os.remove(image_path_out)
            #     return None, image_path
            #
            # else:
            os.rename(image_path, image_path + '.bakuppIMG')
            return image_path_out, None

    else:
        # logging.info(f"Image {image_path_out} already exists. Skipping conversion.")
        return image_path_out, None


def replace_img_name_in_line(line, ref, ref_out):

    ref_out = ref_out.replace(' ', '%20')
    fname_in = os.path.basename(ref)
    line_out = line.replace(fname_in, ref_out)

    return line_out


def process_single_imagepath(image_path_list, line, ref, not_reduced):

    image_path_out = None
    for image_path in image_path_list:
        image_path_out = process_single_img_name(image_path)
        if image_path_out is not None:
            image_path = image_path.replace(' ', '%20')
            ref_out = get_out_ref(ref, image_path_out)
            image_path_out, not_reduced_path = convert_image(image_path, image_path_out)
            if not_reduced_path is not None:
                not_reduced.append(not_reduced_path)
            if image_path_out is not None:
                line = replace_img_name_in_line(line, ref, ref_out)

    return line, not_reduced, image_path_out


def process_line_for_img_optimization(line, img_files):

    refs = get_image_refs_of_line(line)
    not_reduced = []
    image_path_out = None

    for ref in refs:
        image_path_list = get_absolute_img_path(ref, img_files)
        if image_path_list is not None:
            # you might have had non-unique filenames, so you might have multiple matches
            # especially happening if you import from Google Docs
            convert_ON = decide_whether_to_convert(image_path = image_path_list[0])
            if convert_ON:
                line, not_reduced, image_path_out = process_single_imagepath(image_path_list, line, ref, not_reduced)
        else:
            if 'http' not in ref:
                logging.warning(f"Image {ref} not found in the image files.")

    return line, image_path_out


if __name__ == "__main__":

    logging.basicConfig(level=logging.INFO)
    args = parse_args_to_dict()

    process_md_files_for_optimization(input_folder = args["input_folder"])