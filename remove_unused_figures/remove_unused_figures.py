import argparse
import glob
import logging
import os
import re


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


def get_all_files(input_folder, ext = '*.md'):

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
    return files


def get_disk_use(files):
    sizes = [os.path.getsize(f) for f in files]
    total_size = sum(sizes)
    return total_size


def get_kb_files(args):
    md_files = get_all_files(args["input_folder"])
    md_size = get_disk_use(md_files)
    logging.info(f"Total size of .md files: {md_size/10**6:.2f} MB")
    logging.info(f"Average md file size: {md_size/len(md_files)/10**3:.2f} kB")

    img_files = get_all_files(args["input_folder"], ext=['*.png', '*.jpg', '*.jpeg', '*.gif', '*.svg'])
    img_size = get_disk_use(img_files)
    logging.info(f"Total size of image files: {img_size/10**9:.2f} GB")
    logging.info(f"Average image file size: {img_size/len(img_files)/10**3:.2f} kB")

    return md_files, img_files


def return_image_paths(matches):

    image_paths = []
    for ms in matches:
        if ms is not None:
            if '![[' in ms:
                image_path = ms.split('[[')[1].split(']]')[0]
                image_paths.append(image_path)
            else:
                image_path = ms.split('](')[1].split(')')[0]
                image_paths.append(image_path)

    if len(image_paths) > 0:
        return image_paths
    else:
        return None


def get_image_refs_of_line(line):

    line = line.replace('> ', '').replace('>', '')

    #pattern1 = '!\[.*\]\(.*.\)'
    pattern2 = r'!\[\[\D*\d*\.\D{3,4}]]' # https://stackoverflow.com/q/68813348
    pattern3 = '!\[[^\]]*\]\((.*?)\s*("(?:.*[^"])")?\s*\)' # https://stackoverflow.com/a/44227600

    #match1 = [x.group() for x in re.finditer(pattern1, line)]
    match2 = [x.group() for x in re.finditer(pattern2, line)]
    match3 = [x.group() for x in re.finditer(pattern3, line)]
    matches = match2 + match3
    image_paths = return_image_paths(matches)

    if image_paths is not None:
        return image_paths
    else:
        return None


def get_image_refs_of_file(f, relative_base_path):

    img_refs = []
    with open(f, 'r') as file:
        lines = file.readlines()
        for line in lines:
            refs = get_image_refs_of_line(line)
            if refs is not None:
                img_refs.append(refs)

    # flatten Python list
    img_refs = [item for sublist in img_refs for item in sublist]

    return img_refs


def get_img_refs_from_md_files(md_files, input_folder):

    img_refs = {}
    for i, f in enumerate(md_files):
        logging.info(f"Reading {f}")
        relative_base_path = os.path.dirname(f).replace(input_folder, '')
        if len(relative_base_path) > 0:
            if relative_base_path[0] == os.path.sep:
                relative_base_path = relative_base_path[1:]
        refs_per_file = get_image_refs_of_file(f, relative_base_path)
        filename = os.path.basename(f).replace('.md', '').replace(' ', '_')
        img_refs[filename] = refs_per_file
        logging.info(f"Found {len(refs_per_file)} image references in {f}")

    #logging.info(f"Found {len(img_refs)} image references in {len(md_files)} .md files.")
    return img_refs


def strip_subdirs_from_imagepaths(img_refs):

    img_refs_stripped = []
    for img in img_refs:
        img_stripped = img.split('/')[-1]
        img_refs_stripped.append(img_stripped)

    return img_refs_stripped


def replace_whitespace_in_fname(fname: str):
    fname_filled = fname.replace(' ', '%20')
    return fname_filled

def fill_whitespaces_in_fnames(img_refs_stripped):

    img_refs_stripped_filled = []
    for img in img_refs_stripped:
        fname_filled = replace_whitespace_in_fname(img)
        img_refs_stripped_filled.append(fname_filled)

    return img_refs_stripped_filled


def check_if_images_on_disk_are_referenced(img_refs, img_files, input_folder):

    # create a folder where all not referenced images are moved
    move_folder = os.path.join(input_folder, 'attachments_not_referenced')
    os.makedirs(move_folder, exist_ok=True)
    moved_files = []
    input_files = []

    img_refs_list = [item for sublist in img_refs.values() for item in sublist]
    img_refs_stripped = strip_subdirs_from_imagepaths(img_refs_list)
    img_refs_stripped = fill_whitespaces_in_fnames(img_refs_stripped)

    for i, filepath in enumerate(img_files):
        img_file = os.path.basename(filepath)
        img_file = replace_whitespace_in_fname(img_file)
        if img_file not in img_refs_stripped:
            moved_file = os.path.join(input_folder, 'attachments_not_referenced', img_file)
            moved_files.append(moved_file)
            input_files.append(filepath)

    return input_files, moved_files, move_folder


def remove_referenced_files(input_files, moved_files, actually_referenced):

    removed = []
    input_out = []
    moved_out = []

    refs_stripped = strip_subdirs_from_imagepaths(actually_referenced)
    for input_file, moved_file in zip(input_files, moved_files):
        filename = os.path.basename(moved_file)
        if filename not in refs_stripped:
            input_out.append(input_file)
            moved_out.append(moved_file)
        else:
            removed.append(filename)

    assert len(moved_out) == len(input_out), "The number of moved files and input files should be the same."

    return input_out, moved_out


def doublecheck_that_not_referenced_in_md_files(md_files, moved_files, input_files):

    assert len(moved_files) == len(input_files), "The number of moved files and input files should be the same."
    actually_referenced = []

    logging.info(f"DOUBLECHECK:")
    for i, md_file in enumerate(md_files):

        logging.info(f"Checking {md_file}")
        with open(md_file, 'r') as file:
            lines = file.readlines()
            file_as_string = ''.join(lines)

        for (input_file, moved_file) in zip(input_files, moved_files):
            basefilename = os.path.basename(moved_file)
            if basefilename in file_as_string:
                actually_referenced.append(moved_file)

    input_out, moved_out = remove_referenced_files(input_files, moved_files, actually_referenced)

    logging.info(f"DOUBLECHECK: Found {len(actually_referenced)} images that are actually referenced in .md files.")
    logging.info(f"DOUBLECHECK: Still {len(moved_out)} images that are not referenced in .md files.")

    # TODO! you could check for unique naming here, as e.g. Google Docs import like just sequential naming, so you
    #  get the same names in multiple folders, and then you would overwrite the files (not_referenced folder)

    return input_out, moved_out


def move_the_unreferenced_files(input_files, moved_files, input_folder, move_folder,
                                move=True):

    logging.info(f"Moving {len(moved_files)} files to {move_folder}...")
    not_moved = []

    if move:
        for i, (input_file, moved_file) in enumerate(zip(input_files, moved_files)):
            try:
                os.rename(input_file, moved_file)
            except Exception as e:
                not_moved.append((input_file, moved_file))
    else:
        logging.warning("Files were not moved, as move=False was set. (DEBUG mode)")

    actually_moved_files = get_all_files(move_folder, ext=['*.png', '*.jpg', '*.jpeg', '*.gif', '*.svg'])
    logging.info(f"Moved {len(actually_moved_files)} files to {move_folder}.")
    freed_up_disk_space = get_disk_use(actually_moved_files)
    logging.info(f"Freed up {freed_up_disk_space / 10 ** 6:.2f} MB of disk space.")


if __name__ == "__main__":

    logging.basicConfig(level=logging.INFO)
    args = parse_args_to_dict()
    md_files, img_files = get_kb_files(args)

    img_refs = get_img_refs_from_md_files(md_files, args["input_folder"])
    input_files, moved_files, move_folder = check_if_images_on_disk_are_referenced(img_refs, img_files, args["input_folder"])
    input_files, moved_files = doublecheck_that_not_referenced_in_md_files(md_files, moved_files, input_files)
    move_the_unreferenced_files(input_files, moved_files, args["input_folder"], move_folder)