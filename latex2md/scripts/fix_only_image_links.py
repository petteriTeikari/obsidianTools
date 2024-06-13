import logging
import os

from latex2md.file_io import get_files
from latex2md.filtering import fix_image_links
from latex2md.utils import parse_args_to_dict

if __name__ == "__main__":

    logging.basicConfig(level=logging.INFO)
    args = parse_args_to_dict()
    md_files = get_files(args["input_folder"], ext=".md")

    for md_file in md_files:
        logging.info(f"Processing {md_file}")

        with open(md_file, "r") as f:
            md_lines = f.readlines()

        md_lines, fixes = fix_image_links(md_lines,
                                          args["input_folder"],
                                          figures_folder = 'figures')

        md_lines, fixes2 = fix_image_links(md_lines,
                                           args["input_folder"],
                                           figures_folder='extra_figures')

        os.rename(md_file, md_file + ".bak")
        with open(md_file, "w") as f:

            logging.info(f"Exporting to {md_file}")
            f.writelines(md_lines)