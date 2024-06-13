import glob
import json
import logging
import os

import bibtexparser
import fnmatch


def is_body_text(line: str):
    is_bodytext = True
    if line == "\n":
        is_bodytext = False
    if '\\section' in line:
        is_bodytext = False
    if '\\subsection' in line:
        is_bodytext = False
    if '\\subsubsection' in line:
        is_bodytext = False
    if '\\begin' in line:
        is_bodytext = False
    if '\\end' in line:
        is_bodytext = False
    if '\\end' in line:
        is_bodytext = False

    return is_bodytext


def remove_extra_linechanges(lines: list):

    lines_out = []
    for line in lines:
        if is_body_text(line):
            line = line.replace("\n", " ")
        lines_out.append(line)

    return lines_out


def remove_comment_lines(lines):
    '''
    WHen you start removing line changes, the extra % can make new "comment lines"
    :param lines:
    :return:
    '''
    lines_out = []
    no_comment_lines = 0
    no_of_percent_signs = 0
    for line in lines:
        if line.startswith("%"):
            no_comment_lines += 1
        elif '%' in line:
            no_of_percent_signs += 1
            if '%\n' in line:
                # e.g. "'\\selectlanguage{english}%\n'" comes out of LyX for some reason
                line = line.replace('%\n', '\n')
                lines_out.append(line)
            elif '\\' in line:
                # you actually used % in the text
                lines_out.append(line)

            elif line.strip().startswith('%'):
                no_comment_lines += 1

            else:
                # raise NotImplementedError(f"Unsupported % in the tex file, implement this: {line}")
                lines_out.append(line)
        else:
            lines_out.append(line)

    logging.debug(f"Removed {no_comment_lines} comment lines")
    logging.debug(f"Found {no_of_percent_signs} % signs in the text")

    return lines_out


def get_absolute_path(figures_folder, image_name, input_folder):

    figures_path = os.path.join(input_folder, figures_folder)
    if not os.path.exists(figures_path):
        logging.error(f"Figures folder not found: {figures_path}")
        raise FileNotFoundError(f"Figures folder not found: {figures_path}")

    matches = glob.glob(os.path.join(figures_path, image_name + ".*"))
    if len(matches) == 1:
        abs_image_path = matches[0]
        rel_image_path = os.path.relpath(abs_image_path, input_folder)
        return abs_image_path, rel_image_path

    else:
        logging.warning(f'ambiguous file parsing, you have same name with multiple extensions?\n'
                        f'{matches}')
        return None, None


def fix_caption_link(caption):

    def get_link_fields(fields):
        link_name = fields[0].replace('[', '')
        link_url = fields[1].replace(')', '')
        return link_name, link_url


    # if link markdown is in the caption
    fields = caption.split('](')
    if len(fields) > 1:
        if len(fields) == 2:
            link_name, link_url = get_link_fields(fields)
            link_out = f'{link_name}||{link_url}'
            caption_out = caption.replace(f'[{link_name}]({link_url})', link_out)
        else:
            # multiple links in the caption
            caption_out = caption
    else:
        # no link block found
        caption_out = caption

    return caption_out


def remove_styling_from_link(caption):

    caption = caption.replace('**', '')
    caption = caption.replace('*', '')
    caption = caption.replace('__', '')
    caption = caption.replace('[', '')
    caption = caption.replace(']', '')

    return caption


def remove_extra_brackets_from_caption(i, caption):

    c0 = caption.split('[')
    if len(c0) > 1:
        c1 = c0[1].split(']')
        caption = c1[0]

    return caption


def clean_caption(caption):

    caption = fix_caption_link(caption)
    caption = remove_styling_from_link(caption)

    return caption


def fix_image_link(i, line, input_folder, figures_folder = 'figures'):

    try:
        startline, caption = line.split('![')
    except Exception as e:
        logging.warning(f'Problem parsing the image link: {line}')
        return line

    try:
        caption, image_link = caption.split(f']({figures_folder}/')
    except Exception as e:
        logging.warning(f'Problem parsing the image caption: {caption}{os.pathsep}')
        return line

    try:
        image_name, the_rest = image_link.split(f')')
    except Exception as e:
        logging.warning(f'Problem parsing the image name: {image_name}')
        return line

    abs_image_path, rel_image_path = get_absolute_path(figures_folder, image_name, input_folder)
    caption = clean_caption(caption)
    # caption = remove_extra_brackets_from_caption(i, caption)

    try:
        if rel_image_path is None:
            line_out = line
        else:
            line_out = f'![{caption}]({rel_image_path}){the_rest}'
            if startline == '> ':
                line_out = '> ' + line_out
    except Exception as e:
        logging.warning(f'Problem fixing the image link: {line}')

    return line_out


def fix_image_links(lines, input_folder, figures_folder = 'figures'):

    fixes = []

    no_fixed_image_captions = 0
    lines_out = []
    for i, line in enumerate(lines):
        if '![' in line:
            line_out = fix_image_link(i, line, input_folder, figures_folder=figures_folder)
            no_fixed_image_captions += 1
            line_out.replace('*', '')
            fixes.append((i, line, line_out))
        else:
            line_out = line
        lines_out.append(line_out)

    logging.debug(f"Fixed {no_fixed_image_captions} image captions")

    return lines_out, fixes


def import_json_biblio(json_biblio):

    def get_citation_keys_from_json_dict(bibtex_in):
        citation_keys = []
        for item in bibtex_in['items']:
            citation_keys.append(item['citationKey'])

        return citation_keys


    with open(json_biblio, 'r') as f:
        json_data = f.read()
        jsonbib = json.loads(json_data)
        jsonbib['citation_keys'] = get_citation_keys_from_json_dict(jsonbib)

    return jsonbib


def convert_bibtex_to_json(bib_path):

    # https://tex.stackexchange.com/a/268305
    # NOTE! The conversion does not do anything here as these keys came from LyZ - LyX connection
    #  and they are shorter than the BetterBibTex keys that you could get from your Zotero by exporting
    #  your db as "BetterBibTeX JSON" and we need to match the DOI keys to the citation keys in the markdown
    json_path = bib_path.replace('.bib', '.json')
    return_code = os.system(f"pandoc {bib_path} -t csljson -o {json_path}")

    return json_path


def import_bibtex(bib_path):

    # https://stackoverflow.com/a/30769042
    with open(bib_path) as bibtex_file:
        bibtex = bibtexparser.load(bibtex_file)

    return bibtex


def import_biblios(bib_path, json_biblio):

    jsonbib = import_json_biblio(json_biblio)
    bibtex = import_bibtex(bib_path)

    return jsonbib, bibtex


def match_from_master_biblio(to_find, to_find_key, jsonbib):

    item = None
    for item in jsonbib['items']:
        if to_find_key in item:
            if item[to_find_key] == to_find:
                return item

    if item is None:
        logging.warning(f"Could not find the {to_find_key} in the master biblio: {to_find}")
        return None


def get_replace_LUT(jsonbib, bibtex):

    lookup_table = []
    no_not_found = 0

    for bib_entry in bibtex.entries:
        dict_out = {'in_key': bib_entry['ID'], 'in_dict': bib_entry}

        if 'doi' in bib_entry:
            doi = bib_entry['doi']
            match = match_from_master_biblio(to_find=doi, to_find_key='DOI', jsonbib=jsonbib)
            if match is None:
                dict_out['out_key'] = None
                dict_out['out_dict'] = None
            else:
                dict_out['out_key'] = match['citationKey']
                dict_out['out_dict'] = match

        elif 'url' in bib_entry:
            url = bib_entry['url']
            match = match_from_master_biblio(to_find=url, to_find_key='url', jsonbib=jsonbib)
            if match is None:
                dict_out['out_key'] = None
                dict_out['out_dict'] = None
            else:
                dict_out['out_key'] = match['citationKey']
                dict_out['out_dict'] = match

        else:
            logging.warning(f"DOI nor URL found in the Bibtex: {bib_entry['ID']} - Cannot get an updated citation key")
            dict_out['out_key'] = None
            dict_out['out_dict'] = None
            no_not_found += 1

        lookup_table.append(dict_out)

    if no_not_found > 0:
        logging.warning(f"Could not find {no_not_found} citation keys")

    return lookup_table


def get_lookup_table(bib_path, json_biblio):

    logging.info(f"Get the lookup table for the citation keys")
    jsonbib, bibtex = import_biblios(bib_path, json_biblio)
    lookup_table = get_replace_LUT(jsonbib, bibtex)

    logging.info(f"Document bibtex had {len(lookup_table)} citation keys")
    logging.info(f"The 'master' JSON bibllo has {len(jsonbib['citation_keys'])} citation keys")

    return lookup_table


def clean_keys(filtered):

    filtered_out = []

    for item in filtered:

        if not item.replace('[', '').replace('!', '').startswith('\\'):
            if not item.replace('[', '').replace('!', '').startswith('href'):
                fields = item.split('](') # if in an image caption
                item = fields[0]
                assert type(item) == str, f"Item should be a string: {item}"
                fields = item.split('{')
                item = fields[0]
                assert type(item) == str, f"Item should be a string: {item}"
                fields = item.split(')')
                item = fields[0]
                assert type(item) == str, f"Item should be a string: {item}"
                fields = item.split('(')
                item = fields[0]
                assert type(item) == str, f"Item should be a string: {item}"
                item = item.replace('@', '')
                item = item.replace(']', '')
                item = item.replace('[', '')
                item = item.replace(',', '')
                item = item.replace('.', '')
                item = item.replace(';', '')
                item = item.replace(':', '')
                item = item.replace('*', '')
                item = item.replace('!', '')
                item = item.replace('"', '')
                item = item.replace('\\', '')
                item = item.replace('\n', '')
                filtered_out.append(item)
        else:
            logging.debug(f"Found a weird citation key: {item}")

    return filtered_out


def find_match_from_LUT(citationkey, lookup_table):

    for item in lookup_table:
        if item['in_key'] == citationkey:
            return item

    return None


def convert_the_citationkeys(md_lines_out, lookup_table):

    lines_out = []
    replacements = []
    for i, line in enumerate(md_lines_out):

        # https://stackoverflow.com/a/11427183
        lst = line.split(' ')
        filtered = fnmatch.filter(lst, '*@*')

        if len(filtered) > 0:
            cleaned = clean_keys(filtered)
            for citationkey in cleaned:
                match = find_match_from_LUT(citationkey, lookup_table)
                if match is not None:
                    if match['out_key'] is not None:
                        replacements.append((i, citationkey, match['out_key']))
                        line = line.replace(citationkey, match['out_key'])
                else:
                    logging.warning(f"Could not find the citation key in the lookup table: {citationkey}")

        lines_out.append(line)

    assert len(md_lines_out) == len(lines_out), "The number of lines should be the same after the conversion"
    logging.info(f"Replaced {len(replacements)} citation keys")

    return lines_out


def convert_bibtex_to_betterbibtex_keys(md_lines_out, bib_path, json_biblio):

    lookup_table = get_lookup_table(bib_path, json_biblio)
    md_lines_out_conv = convert_the_citationkeys(md_lines_out, lookup_table)

    return md_lines_out_conv


def quick_replace(md_lines_out):

    lines_out = []
    for line in md_lines_out:
        line = line.replace('{width="1\\columnwidth"}', '')
        line = line.replace('{width="0.9\\columnwidth"}', '')
        line = line.replace('{width="0.8\\columnwidth"}', '')
        line = line.replace('{width="0.7\\columnwidth"}', '')
        line = line.replace('{width="0.6\\columnwidth"}', '')
        line = line.replace('{width="2.0\\columnwidth"}', '')
        lines_out.append(line)

    return lines_out


def clean_md_files(md_lines, input_folder, bib_path, json_biblio):
    '''
    Clean the markdown files, possible glithces from the conversion:
    1) Links in alt-texts, e.g. ![[alt tex link](alt text url)](figure.png) which will not render your image
    2) in LyX/Tex, you don't have file extensions for images, but in markdown you need them
    :param md_lines:
    :return:
    '''

    md_lines_out, fixes = fix_image_links(md_lines, input_folder, figures_folder='figures')
    md_lines_out, fixes2 = fix_image_links(md_lines_out, input_folder, figures_folder='extra_figures')
    md_lines_out = quick_replace(md_lines_out)
    md_lines_out = convert_bibtex_to_betterbibtex_keys(md_lines_out, bib_path, json_biblio)

    return md_lines_out


def remove_brackets(line):

    fixes = []
    image_caption = False

    line_out = line
    fields_init = line.split('[@')
    if '!' in fields_init[0]:
        # if the citation was found from figure caption
        fields_init = fields_init[1:]
        image_caption = True

    if not image_caption:
        for field in fields_init:
            if '@' in field:
                # multiple keys inside the brackets
                citations_on_field = field
                inside_brackets = '@' + field.split(']')[0]
                substring_in = '[' + inside_brackets + ']'
                substring_out = inside_brackets
                line_out = line_out.replace(substring_in, substring_out)
                fixes.append((line, line_out))

    else:
        if line.startswith('![@'):
            a = 1 # todo, the normal citation without brackets, e.g. ![@cite1](image.png)
        else:
            b = 2 # todo, the citation with brackets in the image caption, e.g. ![[@cite1]](image.png)

    return line_out, fixes


def remove_brackets_around_multiple_keys(md_lines_out):

    fixes_out = []
    lines_out = []
    for line in md_lines_out:
        if '[@' in line:
            line_out, fixes = remove_brackets(line)
            lines_out.append(line_out)
            if fixes is not None:
                fixes_out.append(fixes)
        else:
            lines_out.append(line)

    return lines_out, fixes_out


def fix_citations(md_lines, input_folder, bib_path, json_biblio):

    lookup_table = get_lookup_table(bib_path, json_biblio)
    md_lines_out = convert_the_citationkeys(md_lines, lookup_table)
    md_lines_out, fixes_out = remove_brackets_around_multiple_keys(md_lines_out)

    if len(fixes_out) > 0:
        logging.info(f"Fixed {len(fixes_out)} multiple citation keys")

    return md_lines_out