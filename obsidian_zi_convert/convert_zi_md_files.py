import argparse
import glob
import json
import os

import logging
import re

logger = logging.getLogger(__name__)

#import bibtexparser
#from pybtex.database.input import bibtex # https://stackoverflow.com/a/30769042

# If you want to interact directly with Zotero?
# https://forums.zotero.org/discussion/87671/a-new-python-tool-kit-for-interacting-with-the-locally-hosted-zotero-database


def parse_args_to_dict():

    def print_dict_to_logger(dict_in: dict, prefix: str = ""):
        for k, v in dict_in.items():
            logger.info("{}{}: {}".format(prefix, k, v))

    parser = argparse.ArgumentParser(
        description="Convert Markdown (.md) files from Obsidian with Zotero Integration (Better BibTeX) "
                    "keys to hardcoded hyperlinks"
    )
    parser.add_argument(
        "-i",
        "--input-bibtex-file",
        type=str,
        required=True,
        default="/home/petteri/Dropbox/manuscriptDrafts/obsidian_zi_convert/input.bib",
        help="You need to find the matches to the keys used in the doc from here",
    )
    parser.add_argument(
        "-output",
        "--output-bibtex-file",
        type=str,
        required=True,
        default="/home/petteri/Dropbox/manuscriptDrafts/obsidian_zi_convert/output.bib",
        help="Save every found key to this output bibtex. I.e. if you only used a subset of the bibtex entries",
    )
    parser.add_argument(
        "-md",
        "--md-files-dir",
        type=str,
        required=True,
        default='/home/petteri/Dropbox/manuscriptDrafts/obsidian_zi_convert/CVT_test',
        help="Where the .md files are located. Assuming that this is one vault with shared Zotero db",
    )

    args_dict = vars(parser.parse_args())
    print_dict_to_logger(args_dict)

    return args_dict


def list_md_files_in_dir(dir_in: str):
    # TODO! recursive for subdirs?
    # files = [f for f in os.listdir(dir_in) if f.endswith('.md')]
    files = glob.glob(dir_in + '/**/*.md', recursive=True)
    logging.info("Found {} .md files in {}".format(len(files), dir_in))
    for f in files:
        logging.info(f)
    return files


def create_bibtex(bib_path: str):
    # TODO!
    return None


def get_citation_keys_from_json_dict(bibtex_in):

    citation_keys = []
    for item in bibtex_in['items']:
        citation_keys.append(item['citationKey'])

    return citation_keys

def import_bibtex_files(input: str, output: str,
                        parser_method = 'betterbibtex_json'):

    if not os.path.exists(input):
        raise FileNotFoundError("Input bibtex file not found: {}".format(input))
    else:
        logging.info("Found input bibtex file: {}".format(input))

    if parser_method == 'pybtex':
        # loses urls
        parser = bibtex.Parser()
        bibtex_in = parser.parse_file(input)
        raise NotImplementedError("pybtex not implemented yet")
    elif parser_method == 'bibtexparser':
        # does not accept patents
        with open(input) as bibtex_file:
            bibtex_in = bibtexparser.load(bibtex_file)
        raise NotImplementedError("bibtexparser not implemented yet")
    elif parser_method == 'betterbibtex_json':
        with open(input, 'r') as f:
            json_data = f.read()
        bibtex_in = json.loads(json_data)
        bibtex_in['citation_keys'] = get_citation_keys_from_json_dict(bibtex_in)
    else:
        raise ValueError("Parser method not recognized: {}".format(parser_method))

    logging.info("Bibtex file with {} biblio entries".format(len(bibtex_in['items'])))

    if not os.path.exists(output):
        logging.warning("Output bibtex file not found: {}, creating a new one".format(output))
        bibtex_out = create_bibtex(bib_path=output)
    else:
        # in this option, you are appending to an existing one
        bibtex_out = output

    return bibtex_in, bibtex_out


def process_md_files(md_files: list, bibtex_in, bibtex_out,
                     write_out: bool = True):

    nonfound_keys = []
    markdown_links = []

    for md_file in md_files:
        logging.info("Processing file: {}".format(md_file))

        md_file_lines_out, markdown_links_per_md, keys_not_matched = (
            convert_md_file(md_file=md_file, bibtex_in=bibtex_in, bibtex_out=bibtex_out))

        nonfound_keys += keys_not_matched
        markdown_links += markdown_links_per_md

        # write the .md file to disk
        if write_out:
            with open(md_file, 'w') as f:
                logging.info("Writing to file: {}".format(md_file))
                f.writelines(md_file_lines_out)
        else:
            logging.info("DEBUG MODE ON | Not writing to file: {}".format(md_file))

    return nonfound_keys, markdown_links


def clean_figure_captionm_word(word):

    # common problem now that the citation key is at the end of the field touching ]
    # e.g. @palmqvistBloodBiomarkersImprove2023](Pasted%20image%2020240429112435
    word = word.replace('![', '')
    word_split = word.split(']')
    if len(word_split) > 1:
        word = word_split[0]

    return word


def process_figure_field(line, bibtex_in):

    # You cannot have []() type of links inside the alt text field (at least in Obsidian, the figure is not
    # rendered correctly anymore
    # Quick fix then to display the name (year), and link on the caption (separately)

    line_out = line
    words = line.split(' ')

    key_match = []
    key_not_founds = []

    for word in words:
        if word.startswith('@'):
            word = clean_figure_captionm_word(word)
            markdown_hyperlink, extra_suffix, key_found, key_not_found = (
                convert_citation(word=word, bibtex_in=bibtex_in, fig_caption=True))
            if markdown_hyperlink is not None:
                line_out = line_out.replace(word, markdown_hyperlink)
                key_match.append((markdown_hyperlink, key_found))
            else:
                key_not_founds.append(key_not_found)

    return line_out, key_match, key_not_founds


def process_figure_caption(line, line_tmp, bibtex_in, bibtex_out):
    line, key_match, key_not_founds = process_figure_field(line, bibtex_in)
    return line, key_match, key_not_founds


def get_author_naming(entry):

    author = entry['creators']

    if len(author) == 0:
        logging.warning('No author field for entry: @{}'.format(entry['citationKey']))
        try:
           name = entry['publicationTitle']
        except KeyError:
            try:
                name = entry['libraryCatalog']
            except KeyError:
                logging.error('Work on parsing the articles without authors, e.g. editorials')

    elif len(author) == 1:
        try:
            name = author[0]['lastName']
        except KeyError:
            # when you don't have last and first name separateld
            name = author[0]['name'].split(' ')[1]

    elif len(author) == 2:
        try:
            name = author[0]['lastName'] + ' & ' + author[1]['lastName']
        except KeyError:
            name = author[0]['name'].split(' ')[1] + ' & ' + author[1]['name'].split(' ')[1]

    else:
        try:
            name = author[0]['lastName'] + ' et al.'
        except KeyError:
            name = author[0]['name'].split(' ')[1] + ' et al.'

    # remove extra brackets (if there are, e.g. around Rosa-Neto type of names)
    # name = name.replace('{', '').replace('}', '')

    return name


def get_article_hyperlink(entry, autocorrect_doi = True):

    # hyperlink to the article
    if 'url' in list(entry.keys()):
        hyperlink = entry['url']
        if autocorrect_doi:
            if 'doi' in list(entry.keys()):
                # automatically create DOI hyperlinks if there is a DOI
                hyperlink = 'https://doi.org/' + entry['DOI']
    elif 'DOI' in list(entry.keys()):
        hyperlink = 'https://doi.org/' + entry['DOI']
    else:
        logging.warning("No URL/DOI found in entry: @{}".format(entry['citationKey']))
        hyperlink = None

    return hyperlink


def return_year_from_date(date):
    # https://stackoverflow.com/a/61694805
    match = re.search(r'\b\d{4}\b', date)
    if match:
        year = str(int(match.group(0)))
    else:
        year = '????'
    return year

def get_year(entry):
    # TODO! remove month and day if you want, bibtexparser/pybtex knew how to do this, but not json parsing
    try:
        date = entry['date']
        date = return_year_from_date(date)
    except KeyError:
        if entry['itemType'] == 'patent':
            date = entry['issueDate']
            date = return_year_from_date(date)
        else:
            logging.warning("No date found in entry: @{}".format(entry['citationKey']))
            date = '????'

    if date == '????':
        logging.warning("No year found (or problem parsing) in entry: @{}".format(entry['citationKey']))

    return date


def get_hardcoded_citation_from_entry(entry, bibtex_out, fig_caption: bool = False):

    name = get_author_naming(entry)
    year = get_year(entry)
    citation_string = name + ' (' + year + ')'

    # hyperlink to the article
    hyperlink = get_article_hyperlink(entry)

    # markdown hyperlink
    if hyperlink is not None:
        if fig_caption:
            markdown_hyperlink = f'({citation_string}||{hyperlink})'
        else:
            markdown_hyperlink = f'[{citation_string}]({hyperlink})'
    else:
        markdown_hyperlink = None

    return markdown_hyperlink


def clean_text_key(word):

    word_out = word.replace('@', '')

    # the citation might not be followed by a whitespace
    word_out = word_out.split(')')[0]
    word_out = word_out.split(';')[0]
    word_out = word_out.split(',')[0]
    word_out = word_out.split('.')[0]
    word_out = word_out.split('?')[0]
    word_out = word_out.split(':')[0]
    word_out = word_out.split('\n')[0]
    word_out = word_out.rstrip()

    # if 'huangGlymphaticSystemDysf' in word:
    #     word = 11

    return word_out


def convert_citation(word, bibtex_in, fig_caption:bool = False):

    db_keys_list = bibtex_in['citation_keys'] # list(bibtex_in.entries_dict.keys())
    text_key = clean_text_key(word)

    extra_suffix = None
    if '@'+text_key != word:
        # extra crap after the citation key, e.g ", ", or ")", or ";"
        extra_suffix = word.split('@'+text_key)[1]

    try:
        entry_index = db_keys_list.index(text_key)
        entry = bibtex_in['items'][entry_index]
        markdown_hyperlink = get_hardcoded_citation_from_entry(entry, bibtex_in, fig_caption)
        key_found = bibtex_in['citation_keys'][entry_index]
        key_not_found = None

    except ValueError:
        entry_index, markdown_hyperlink, key_found = None, None, None
        key_not_found = text_key
        logging.warning("Key not found in bibtex: @{}".format(text_key))

    return markdown_hyperlink, extra_suffix, key_found, key_not_found

def process_text_line(line, line_tmp, bibtex_in, bibtex_out):

    # if 'huangGlymphaticSystemDysf' in line:
    #     print('here')

    # There might be extra spaces, e.g. ( @citationKey) that could be converted to (@citationKey)

    line_out = ''
    words = line.split(' ')
    keys_not_found = []
    markdown_hyperlinks = []

    for word in words:

        key_found, key_not_found = None, None
        if word.startswith('@'):
            markdown_hyperlink, extra_suffix, key_found, key_not_found = convert_citation(word, bibtex_in)

            if markdown_hyperlink is not None:
                markdown_tuple = (key_found, markdown_hyperlink)
                markdown_hyperlinks.append(markdown_tuple)

                if extra_suffix is not None:
                    word_out = markdown_hyperlink + extra_suffix
                else:
                    word_out = markdown_hyperlink

                word = word_out

            if key_not_found is not None:
                keys_not_found.append(key_not_found)

        elif word.startswith('![@'):
            # you have a figure caption with a citation key here not caught by initial check,
            # e.g. when your word is the 4th or something on the line with empty entries
            # ['>', '', '', '![@palmqvistBloodBiomarkersImprove2023](Pasted%20image%2020240429112435.png)\n']
            word, key_match, key_not_founds = process_figure_field(word, bibtex_in)


        if line_out == '':
            # the first word
            line_out += word
        else:
            # rest of the words of the line
            line_out += ' ' + word

    return line_out, markdown_hyperlinks, keys_not_found


def convert_md_file(md_file, bibtex_in, bibtex_out):

    no_figure_captions = 0

    with open(md_file, 'r') as f:
        lines = f.readlines()

    lines_out = []
    keys_matched = []
    keys_not_matched = []
    markdown_links = []

    for line in lines:
        # remove possible quotes first, processing is the same, whether the figure or text is quoted or not
        line_tmp = line.replace('> ', '').replace('>', '')

        # Remove spaces to the left of the string:
        line_tmp = line_tmp.lstrip()

        keys_found, keys_not_found = None, None

        if line_tmp.startswith('!['):
            no_figure_captions += 1
            line, key_match, key_not_founds = process_figure_caption(line, line_tmp, bibtex_in, bibtex_out)

        else:
            # process the text
            if "@" in line:
                # only if the line has a citation key
                line, markdown_hyperlinks, keys_not_found = (
                    process_text_line(line, line_tmp, bibtex_in, bibtex_out))

                markdown_links += markdown_hyperlinks

        lines_out.append(line)

        if keys_not_found is not None:
            keys_not_matched += keys_not_found

    logging.debug("Found {} figure captions and {} text citations in {}".
                 format(no_figure_captions, len(markdown_links), md_file))

    return lines_out, markdown_links, keys_not_matched


if __name__ == "__main__":

    logging.basicConfig(level=logging.INFO)
    args = parse_args_to_dict()

    md_files = list_md_files_in_dir(args['md_files_dir'])

    bibtex_in, bibtex_out = (
        import_bibtex_files(input=args['input_bibtex_file'],
                            output=args['output_bibtex_file'])
    )

    nonfound_keys, markdown_links = (
        process_md_files(md_files=md_files, bibtex_in=bibtex_in, bibtex_out=bibtex_out))

    # TODO! does not include key errors in figure captions, atm see the debug printouts during processing
    logging.info("Keys not found from body text:")
    for key in nonfound_keys:
        logging.warning(" @{}".format(key))
    logging.info("Markdown link conversion (tuples):\n {}".format(markdown_links))

    logging.info("Conversion done!")
