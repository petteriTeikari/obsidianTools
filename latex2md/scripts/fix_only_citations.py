import logging
import os

from latex2md.file_io import get_files, get_bib_path
from latex2md.filtering import fix_citations
from latex2md.utils import parse_args_to_dict

if __name__ == "__main__":

    logging.basicConfig(level=logging.INFO)
    args = parse_args_to_dict()
    md_files = get_files(args["input_folder"], ext=".md")

    for md_file in md_files:
        logging.info(f"Processing {md_file}")

        with open(md_file, "r") as f:
            md_lines = f.readlines()

        bib_path = get_bib_path(args["input_folder"])
        md_lines = fix_citations(md_lines,
                                 args["input_folder"],
                                 bib_path,
                                 args["json_biblio"])

        os.rename(md_file, md_file + ".bak")
        with open(md_file, "w") as f:

            logging.info(f"Exporting to {md_file}")
            f.writelines(md_lines)