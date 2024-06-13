import argparse
import logging
import os


def parse_args_to_dict():

    parser = argparse.ArgumentParser(
        description="Clean the .tex file a bit for better conversion to markdown with Pandoc."
    )
    parser.add_argument(
        "-i",
        "--input-folder",
        type=str,
        required=True,
        default="/home/petteri/Dropbox/KnowledgeBase/Art",
        help="Where is / are your .tex files located?",
    )

    args_dict = vars(parser.parse_args())

    return args_dict


def get_files(folder, ext=".md"):

    files = []
    for root, _, filenames in os.walk(folder):
        for filename in filenames:
            if filename.endswith(ext):
                files.append(os.path.join(root, filename))

    return files


def clean_extra_refs_in_figures(line):

    _, fig = line.split("[!")
    try:
        keep, extra = fig.split("](%")
    except ValueError:
        keep = fig
        extra = ""

    keep = '!' + keep

    return keep


def clean_notion_import_md(lines):
    """
    Clean the .md file a bit for better conversion to markdown with Pandoc.
    """

    new_lines = []
    fixes = []

    for line in lines:
        line = line.replace("> ", "") # remove quotes
        if line.startswith("[!"):
            line_out = clean_extra_refs_in_figures(line)
            fixes.append((line, line_out))
        else:
            line_out = line
        new_lines.append(line_out)

    return new_lines


if __name__ == "__main__":

    logging.basicConfig(level=logging.INFO)
    args = parse_args_to_dict()
    md_files = get_files(args["input_folder"], ext=".md")

    for md_file in md_files:

        logging.info(f"Cleaning {md_file}")

        # Read the .md file
        with open(md_file, "r") as f:
            lines = f.readlines()

        # clean the .md file
        new_lines = clean_notion_import_md(lines)

        # write the cleaned .md file
        os.rename(md_file, md_file + ".bak")
        with open(md_file, "w") as f:
            f.writelines(new_lines)