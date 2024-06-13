import glob
import json
import logging
import os


def get_files(input_folder, ext: str = ".tex"):

    if ext == '.tex':
        logging.info(f"Importing .tex files from {input_folder}")
        files = glob.glob(os.path.join(input_folder, "*.tex"))

    if ext == '.md':
        logging.info(f"Importing .md files from {input_folder}")
        files = glob.glob(os.path.join(input_folder, "*.md"))

    elif ext == '.bib':
        logging.info(f"Importing .bib files from {input_folder}")
        files = glob.glob(os.path.join(input_folder, "*.bib"))

    return files


def import_tex_file(tex_file: str):
    # TODO! auto UTF8 encoding?
    # https://tex.stackexchange.com/a/87486
    # https://pandoc.org/MANUAL.html#character-encoding
    try:
        with open(tex_file, "r") as f:
            lines = f.readlines()
    except Exception as e:
        logging.error(f"Failed to import .tex file: {e}")
        try:
            logging.info("Trying to import with latin-1 encoding")
            with open(tex_file, "r", encoding='latin-1') as f:
                lines = f.readlines()
        except Exception as e:
            logging.error(f"Failed to import .tex file with latin-1 encoding: {e}")
            raise FileNotFoundError(f"Failed to import .tex file: {e}")

    return lines


def export_tex_file(tex_file, lines_out):
    '''
    Export the cleaned tex file, note you don't want to write line-by-line,
    as we just cleaned the extra line changes
    :param tex_file:
    :param lines_out:
    :return:
    '''
    tex_file_out = tex_file.replace(".tex", "_cleaned.tex")
    logging.info(f"Exporting to {os.path.split(tex_file_out)[1]}")
    single_string = "".join(lines_out)
    with open(tex_file_out, "w") as f   :
        f.write(single_string)

    return tex_file_out


def get_bib_path(input_folder):

    bib_files = get_files(input_folder, ext=".bib")
    if len(bib_files) > 1:
        logging.error('Found multiple .bib files!')
        raise FileNotFoundError(f"Multiple .bib files found: {bib_files}")
    elif len(bib_files) == 0:
        logging.error('No .bib files found!')
        raise FileNotFoundError(f"No .bib files found in the folder: {input_folder}")
    else:
        logging.info(f"Found .bib file: {os.path.split(bib_files[0])[1]}")
        return bib_files[0]

def convert_to_markdown(tex_file_out):

    md_file = tex_file_out.replace(".tex", ".md")
    input_folder = os.path.split(tex_file_out)[0]
    bib_path = get_bib_path(input_folder)
    logging.info(f"Converting .tex to Markdown (Pandoc): {os.path.split(md_file)[1]}")
    # TODO! Python API? Obviously you also need Pandoc installed on your machine
    try:
        # https://stackoverflow.com/a/62990248
        # https://superuser.com/a/1161832
        return_code = os.system(f"pandoc --wrap=none --citeproc --bibliography={bib_path} "
                                f"-o {md_file} {tex_file_out}")
        if return_code != 0:
            raise Exception("Pandoc failed")
    except Exception as e:
        logging.error(f"Pandoc failed: {e}")
        logging.error(f"You most likely have to manually fix some glitch in your .tex or .bib file?\n"
                      f"Check the line and column of the error and fix it? Often like extra ^ causing issues.")
        raise Exception("Pandoc failed")

    if not os.path.exists(md_file):
        raise FileNotFoundError(f"Markdown file not found: {md_file}")

    return md_file, bib_path


def import_markdown_file(md_file):

    with open(md_file, "r") as f:
        lines = f.readlines()

    return lines


def export_md_file(tex_file, md_lines_out):

    md_file = tex_file.replace(".tex", ".md")
    logging.info(f"Exporting to {os.path.split(md_file)[1]}")
    single_string = "".join(md_lines_out)
    with open(md_file, "w") as f:
        f.write(single_string)


def delete_temp_files(input_folder):

    for root, dirs, files in os.walk(input_folder):
        for file in files:
            if file.endswith("_cleaned.tex") or file.endswith("cleaned.md"):
                os.remove(os.path.join(root, file))
                logging.debug(f"Removed temp file: {file}")


