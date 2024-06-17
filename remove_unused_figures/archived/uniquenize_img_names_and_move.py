import argparse
import glob
import hashlib
import logging
import os
import re
import time
from copy import deepcopy

from remove_unused_figures import get_kb_files, get_img_refs_from_md_files


def parse_args_to_dict():

    parser = argparse.ArgumentParser(
        description="Ensure that all the images have unique names and are in one place. "
                    "You need to run this script e.g. when doing imports from Google Docs, LaTeX/LyX, Notion"
    )
    parser.add_argument(
        "-i",
        "--input-folder",
        type=str,
        required=True,
        default="/home/petteri/Dropbox/KnowledgeBase",
        help="Knowledge base folder.",
    )
    parser.add_argument(
        "-o",
        "--output-folder",
        type=str,
        required=True,
        default="/home/petteri/Dropbox/KnowledgeBase",
        help="Where you want all your attachments to be moved to."
    )
    args_dict = vars(parser.parse_args())

    return args_dict


def try_to_find_image_in_kb(im_ref, paths):

    def find_all(name, path):
        result = []
        for root, dirs, files in os.walk(path):
            if name in files:
                result.append(os.path.join(root, name))
        return result


    def try_to_pick_one(res, abs_path):
        base_dir = os.path.dirname(abs_path)
        fields = base_dir.split(os.path.sep)
        res_out = []
        for r in res:
            if fields[-1] in r and fields[-2] in r:
                res_out.append(r)
        if len(res_out) == 0:
            return None

        return res_out


    ref = os.path.basename(im_ref)
    ref_to_find = ref.replace('%20', ' ')
    res = find_all(ref_to_find, paths['input_folder'])
    if len(res) > 0:
        if len(res) > 1:
            res = try_to_pick_one(res, abs_path = paths['im_absolute'])
            if res is None:
                logging.warning(f"Multiple files found for {ref_to_find}.")
                return None, True

            if len(res) > 1:
                logging.warning(f"Multiple files found for {ref_to_find}.")
                return None, True
            else:
                absolute_path = res[0]
        else:
            absolute_path = res[0]
    else:
        return None, False

    paths['im_absolute'] = absolute_path
    # in relation to the md_relative:
    paths['im_relative'] = '../' + paths['im_absolute'].replace(paths['input_folder'], '')[1:]

    return paths, False


def guess_img_location(im_ref, md_file, input_folder, output_folder):
    '''
    Guess as in the im_ref can be at worst inconsistent
    Args:
        im_ref:
        md_file:
        input_folder:

    Returns:

    '''

    paths = {}
    paths['input_folder'] = input_folder
    paths['output_folder'] = output_folder
    paths['md_relative'] = os.path.dirname(md_file).replace(input_folder, '')[1:]
    md_fix = False

    im_ref_fields = im_ref.split(os.path.sep)
    if len(im_ref_fields) > 1:
        if im_ref_fields[0] == paths['md_relative']:
            # if the subfolder name is already in the relative reference
            paths['im_relative'] = os.path.join(im_ref)
        elif im_ref_fields[1] == 'Attachments':
            # e.g. 'Eye/Attachments/image108.jpg'
            paths['im_relative'] = os.path.join(im_ref)
        else:
            paths['im_relative'] = os.path.join(paths['md_relative'], im_ref)
    else:
        paths['im_relative'] = os.path.join(paths['md_relative'], 'Attachments', im_ref)

    paths['im_absolute'] = os.path.join(input_folder, paths['im_relative'].replace('%20', ' '))
    if len(paths['md_relative']) > 0:
        paths['out_relative'] = os.path.join('../..', output_folder.replace(input_folder, '')[1:])
    else:
        paths['out_relative'] = os.path.join('..', output_folder.replace(input_folder, '')[1:])

    if paths['out_relative'] in im_ref:
        # this path has been converted already
        return None, False

    if not os.path.exists(paths['im_absolute']):
        abs_path = paths['im_absolute']
        if 'http' not in paths['im_absolute']:
            # try to find the image in the knowledge base
            paths_copy = deepcopy(paths)
            paths, multiple_found = try_to_find_image_in_kb(im_ref=im_ref,
                                                            paths=paths)
            if paths is None:
                # try if this is already in the output folder
                base_dir = os.path.dirname(paths_copy['im_relative'])
                possible_path = abs_path.replace(base_dir, paths_copy['out_relative']).replace('..', '')
                possible_path = possible_path.replace(' ', '_')
                if os.path.exists(possible_path):
                    paths = paths_copy
                    paths['im_absolute'] = possible_path
                    fname = os.path.basename(possible_path)
                    paths['im_relative'] = os.path.join(paths['out_relative'], fname)
                    md_fix = True
                else:
                    logging.error(f"(2nd) Image {abs_path} does not exist.")
                    return None, False
        else:
            return None, False

    return paths, md_fix


def check_if_existing_image_is_the_same(in_path, out_path):

    debug_dict = {}
    debug_dict['in_size'] = os.path.getsize(in_path)
    debug_dict['out_size'] = os.path.getsize(out_path)
    debug_dict['in_path'] = in_path
    debug_dict['out_path'] = out_path

    if debug_dict['in_size'] == debug_dict['out_size']:
        # This should be the same file if the sizes are the same
        return None, None
    else:
        hashlib.sha1().update(str(time.time()).encode("utf-8"))
        hash = hashlib.sha1().hexdigest()[:10]
        fname = os.path.basename(out_path)
        fname, ext = os.path.splitext(fname)
        out_updated = out_path.replace(f'{ext}', f'_{hash}{ext}').replace('%20', ' ').replace(' ', '_')

        return out_updated, debug_dict


def define_filenames_and_paths(paths, im_ref, input_folder, md_fix,
                               skip_existing = True):

    rename = True
    move = True

    names = {}
    names['im_ref_in'] = im_ref

    names['im_ref_out'] = os.path.join(paths['out_relative'], os.path.basename(im_ref))
    names['im_ref_out'] = names['im_ref_out'].replace('%20', ' ').replace(' ', '_')
    names['im_absolute_in'] = paths['im_absolute'].replace('//', '/')

    fname_out = names['im_ref_out'].replace('%20', ' ').replace(' ', '_')
    names['im_absolute_out'] = os.path.join(input_folder, paths['md_relative'], fname_out)

    if skip_existing:
        if os.path.exists(names['im_absolute_out']):
            out_updated, debug_dict = (
                check_if_existing_image_is_the_same(in_path=names['im_absolute_in'],
                                                    out_path=names['im_absolute_out']))
            if out_updated is not None:
                names['im_absolute_out'] = out_updated
                fname_out = os.path.basename(out_updated)
                fname_in = os.path.basename(names['im_ref_out'])
                names['im_ref_out'] = names['im_ref_out'].replace(fname_in, fname_out)
            else:
                # logging.info(f"Image {names['im_absolute_out']} already exists. Skipping.")
                if md_fix:
                    return names, True, False
                else:
                    # case where the image is already in the output folder,
                    # so you wanna move the duplicate img away and update the reference
                    return names, True, False

    return names, rename, move


def process_md_file_collect(lines, md_file, im_refs_file,
                            output_folder, input_folder,
                            actually_move_and_save = True):

    debug = {}
    debug['conversions'] = []
    debug['not_found'] = []
    debug['already_exists'] = []

    lines_as_string = ''.join(lines)
    for im_ref in im_refs_file:
        paths, md_fix = guess_img_location(im_ref, md_file, input_folder, output_folder)
        if paths is not None:
            names, rename, move = define_filenames_and_paths(paths, im_ref, input_folder, md_fix)

            if rename:
                lines_as_string = lines_as_string.replace(names['im_ref_in'], names['im_ref_out'])

                if move:
                    if actually_move_and_save:
                        debug['conversions'].append((names['im_ref_in'], names['im_ref_out']))
                        os.makedirs(os.path.dirname(names['im_absolute_out']), exist_ok=True)
                        os.rename(names['im_absolute_in'], names['im_absolute_out'])
                else:
                    if actually_move_and_save:
                        debug['already_exists'].append((names['im_ref_in'], names['im_ref_out']))
                        base_dir = os.path.dirname(names['im_absolute_out'])
                        tmp_dir = os.path.dirname(names['im_absolute_out']) +'_duplicatesToBeDeleted'
                        os.makedirs(tmp_dir, exist_ok=True)
                        os.rename(names['im_absolute_in'], names['im_absolute_out'].replace(base_dir, tmp_dir))

            else:
                if move:
                    a = 1
                else:
                    b = 2
        else:
            debug['not_found'].append(im_ref)

    if actually_move_and_save:
        os.rename(md_file, md_file + '.bakMD')
        with open(md_file, 'w') as f:
            f.write(lines_as_string)

    logging.info(f"Number of images moved: {len(debug['conversions'])}")
    if len(debug['conversions']) > 0:
        logging.debug(f"Images moved: {debug['conversions']}")

    if len(debug['already_exists']) > 0:
        logging.debug(f"Images already existed: {debug['already_exists']}")

    if len(debug['not_found']) > 0:
        logging.debug(f"Images not found: {debug['not_found']}")


if __name__ == "__main__":

    logging.basicConfig(level=logging.INFO)
    args = parse_args_to_dict()
    md_files, img_files = get_kb_files(args)

    img_refs = get_img_refs_from_md_files(md_files, args["input_folder"])

    logging.info(f"Processing {len(md_files)} .md files.")
    for i, md_file in enumerate(md_files):
        logging.info(f"Processing {i+1}/{len(md_files)}: {md_file}")
        fname = os.path.basename(md_file)
        fname, ext = os.path.splitext(fname)
        im_refs_file = img_refs[fname.replace(' ', '_')]

        with open(md_file, 'r') as f:
            lines = f.readlines()
            process_md_file_collect(lines, md_file, im_refs_file,
                                    output_folder=args["output_folder"],
                                    input_folder=args["input_folder"])