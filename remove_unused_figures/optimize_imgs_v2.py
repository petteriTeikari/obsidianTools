import argparse
import glob
import logging
import os
import re
from PIL import Image

from remove_unused_figures import get_disk_use, get_img_refs_from_md_files
from utils import get_image_refs_of_line, create_hash, hash_suffix_str


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


def check_if_conversion_needed(img_ref, input_folder):

    refs = {}
    fname = os.path.basename(img_ref)
    fname, ext = os.path.splitext(fname)
    if ext == '.png':
        refs['ref_out'] = img_ref.replace('.png', '.jpg')
        refs['ref_pathout'] = os.path.join(input_folder, refs['ref_out'].replace('../', ''))
        refs['ref_in'] = img_ref
        refs['ref_pathin'] = os.path.join(input_folder, img_ref.replace('../', ''))
        if os.path.exists(refs['ref_pathout']):
            return None
        else:
            return refs


def optimize_imgs_references(lines, img_files, md_fname, input_folder):

    def save_as_jpg(image_path, image_path_out):
        img = Image.open(image_path)
        img = img.convert('RGB')
        img.save(image_path_out, format='JPEG', subsampling=0, quality=85)

    lines_out = []
    lines_changed= []
    skipped = []
    for line in lines:
        if '![' in line:
            img_refs = get_image_refs_of_line(line)
            for img_ref in img_refs:
                refs = check_if_conversion_needed(img_ref, input_folder=input_folder)
                if refs is not None:
                    line = line.replace(refs['ref_in'], refs['ref_out'])
                    lines_changed.append(line)
                    save_as_jpg(image_path=refs['ref_pathin'],
                                image_path_out=refs['ref_pathout'])
                    os.rename(refs['ref_pathin'], refs['ref_pathin'] + '.bak')
                else:
                    skipped.append(img_ref)

        lines_out.append(line)

    return lines_out, lines_changed, skipped


def rename_extension_of_refs(img_refs, lines, unique_hash):

    hash_string = hash_suffix_str(unique_hash)

    lines_as_str = ''.join(lines)
    for img_ref in img_refs:
        base_name = os.path.basename(img_ref)
        fname, ext = os.path.splitext(base_name)
        if ext == '.jpeg':
            lines_as_str = lines_as_str.replace(f'{base_name}', f'{fname}{hash_string}.jpg')
        elif ext == '.png':
            lines_as_str = lines_as_str.replace(f'{base_name}', f'{fname}{hash_string}.jpg')
        elif ext == '.jpg':
            if len(hash_string) > 0:
                lines_as_str = lines_as_str.replace(f'{base_name}', f'{fname}{hash_string}.jpg')
        elif ext == '.ico':
            a = 1
        #elif ext == '.gif':
        #    lines_as_str = lines_as_str.replace(f'{base_name}', f'{fname}.jpg')
        else:
            a = 1

    return lines_as_str


def process_md_file(md_file, img_files, md_fname, img_refs, input_folder, unique_hash, export_on=True):

    with open(md_file, 'r') as f:
        lines = f.readlines()

    # batch convert all pngs to jpgs, and rename jpeg to jpg on Bash then
    lines_out = rename_extension_of_refs(img_refs, lines, unique_hash)

    os.rename(md_file, md_file + '.bakMDupp')
    with open(md_file, 'w') as f:
        f.writelines(lines_out)


def process_md_files_for_optimization(input_folder, unique_hash=None):

    img_files = get_all_img_files(input_folder)
    md_files = sorted(glob.glob(os.path.join(input_folder, '**', '*.md'), recursive=True))
    img_refs = get_img_refs_from_md_files(md_files, args["input_folder"])

    for i, md_file in enumerate(md_files):
        md_fname = os.path.basename(md_file)
        logging.info(f"Processing {i+1}/{len(md_files)}: {md_fname}")
        fname = os.path.basename(md_file)
        fname, ext = os.path.splitext(fname)
        im_refs_file = img_refs[fname.replace(' ', '_')]

        process_md_file(md_file, img_files, md_fname, im_refs_file, input_folder, unique_hash)


def batch_convert_images(input_folder, quality=85, subsampling=0, unique_hash=None):

    hash_string = hash_suffix_str(unique_hash)

    def correct_format(ext):
        return ext == '.png' or ext == '.jpeg'

    img_files = get_all_img_files(input_folder)
    for i, img_file in enumerate(img_files):
        fname = os.path.basename(img_file)
        fname, ext = os.path.splitext(fname)
        if correct_format(ext):
            logging.info(f"#{i+1}/{len(img_files)}: Converting {fname} to jpg")
            img_file = img_file.replace('%20', ' ')
            img = Image.open(img_file)
            img = img.convert('RGB')
            img_file_out = img_file.replace('.png', '.jpg').replace('.jpeg', '.jpg').replace('.gif', '.jpg')
            img_file_out = img_file_out.replace('.jpg', f'{hash_string}.jpg')
            img.save(img_file_out, format='JPEG', subsampling=subsampling, quality=quality)
            os.rename(img_file, img_file + '.bakIMG')
        elif ext == '.jpg':
            if len(hash_string) > 0:
                logging.info(f"#{i}/{len(img_files)}: Renaming {fname} to {fname}{hash_string}.jpg")
                img_file = img_file.replace('%20', ' ')
                img_file_out = img_file.replace('.jpg', f'{hash_string}.jpg')
                os.rename(img_file, img_file_out)



if __name__ == "__main__":

    logging.basicConfig(level=logging.INFO)
    args = parse_args_to_dict()

    use_hash = True
    if use_hash:
        unique_hash = create_hash()
    else:
        unique_hash = None

    process_md_files_for_optimization(input_folder = args["input_folder"],
                                      unique_hash = unique_hash)
    batch_convert_images(input_folder = args["input_folder"],
                         unique_hash = unique_hash)