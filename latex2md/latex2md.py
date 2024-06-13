import logging
import os

from file_io import import_tex_file, export_tex_file, convert_to_markdown, import_markdown_file, get_files, \
    export_md_file, delete_temp_files
from filtering import remove_comment_lines, clean_md_files
from utils import parse_args_to_dict


def filter_tex_file(tex_file: str):

    lines = import_tex_file(tex_file)
    lines_out = remove_comment_lines(lines)
    # not needed, just use "--wrap=none" with pandoc
    #lines_out = remove_extra_linechanges(lines_out)

    return lines_out


def process_tex_file(tex_file: str, input_folder: str, json_biblio: str):

    logging.info(f"Processing {os.path.split(tex_file)[1]}")
    lines_out = filter_tex_file(tex_file)
    tex_file_out = export_tex_file(tex_file, lines_out)
    md_file, bib_path = convert_to_markdown(tex_file_out)
    md_lines = import_markdown_file(md_file)
    md_lines_out = clean_md_files(md_lines, input_folder, bib_path, json_biblio)
    export_md_file(tex_file, md_lines_out)
    delete_temp_files(input_folder)


if __name__ == "__main__":

    logging.basicConfig(level=logging.INFO)
    args = parse_args_to_dict()
    tex_files = get_files(args["input_folder"], ext=".tex")

    for i, tex_file in enumerate(tex_files):
        process_tex_file(tex_file, args["input_folder"], args["json_biblio"])

    logging.info("All done!")


