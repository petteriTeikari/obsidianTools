import argparse
import logging
import os

from latex2md.file_io import get_files


def parse_args_to_dict():

    parser = argparse.ArgumentParser(
        description="Clean the .tex file a bit for better conversion to markdown with Pandoc."
    )
    parser.add_argument(
        "-i",
        "--input-folder",
        type=str,
        required=True,
        default="/home/petteri/Dropbox/KnowledgeBase/Respiratory",
        help="Where is / are your .tex files located?",
    )
    args_dict = vars(parser.parse_args())

    return args_dict


def reject_line(md_line):

    reject = False
    line_tmp = md_line.replace('> ', '')
    if line_tmp.startswith("style="):
        reject = True

    return reject


def fix_html_image(md_line, image_tag_str):

    line_tmp = md_line.replace('> ', '')
    tag, image_path = line_tmp.split(image_tag_str)
    image_path = image_path.split('"')[1]
    md_line = f"!['']({image_path})\n" # assuming now that you did not have anything else than the img on the line

    return md_line

def clean_docx_import(md_lines, image_tag_str: str = '<img src='):

    lines_out = []
    for md_line in md_lines:

        if not reject_line(md_line):
            if image_tag_str in md_line:
                md_line = fix_html_image(md_line, image_tag_str)

            # remove underlining
            md_line = md_line.replace('<u>', '').replace('</u>', '')

            # remove extra quotes
            md_line = md_line.replace('> ', '').replace('>','')

            # remove extra line changes
            if md_line != '\n':
                md_line = md_line.replace('\n', ' ')

            lines_out.append(md_line)

    return lines_out


if __name__ == "__main__":

    logging.basicConfig(level=logging.INFO)
    args = parse_args_to_dict()
    md_files = get_files(args["input_folder"], ext=".md")

    for i, md_file in enumerate(md_files):
        logging.info(f"Processing {md_file}")
        with open(md_file, "r") as f:
            md_lines = f.readlines()

        md_lines = clean_docx_import(md_lines)

        os.rename(md_file, md_file + ".bak")
        lines_as_single_string = "".join(md_lines)
        with open(md_file, "w") as f:
            logging.info(f"Exporting to {md_file}")
            f.writelines(lines_as_single_string)

    logging.info("All done!")