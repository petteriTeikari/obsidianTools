import argparse


def parse_args_to_dict():

    parser = argparse.ArgumentParser(
        description="Clean the .tex file a bit for better conversion to markdown with Pandoc."
    )
    parser.add_argument(
        "-i",
        "--input-folder",
        type=str,
        required=True,
        default="/home/petteri/Dropbox/manuscriptDrafts/vesselMLOps/obsidiantest",
        help="Where is / are your .tex files located?",
    )

    parser.add_argument(
        "-json",
        "--json-biblio",
        type=str,
        required=True,
        default="/home/petteri/Dropbox/manuscriptDrafts/vesselMLOps/obsidiantest/vessops.json",
        help="Better BibTeX JSON file for the citations",
    )

    args_dict = vars(parser.parse_args())

    return args_dict