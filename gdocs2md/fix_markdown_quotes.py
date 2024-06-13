import argparse
import logging
import os
import re
import shutil
#import pyparsing as pp


def parse_args_to_dict():

    parser = argparse.ArgumentParser(
        description="Convert $QUOTETOBEREPLACED$ left from fix_gdocs_html.py to markdown quotes"
    )
    parser.add_argument(
        "-i",
        "--input-folder",
        type=str,
        required=True,
        default="/home/petteri/Dropbox/KnowledgeBase/",
        help="Where is / are your html files located?",
    )

    args_dict = vars(parser.parse_args())

    return args_dict


def get_import_markdowns(input_folder):

    md_files = []
    for root, dirs, files in os.walk(input_folder):
        for file in files:
            if file.endswith(".md"):
                md_files.append(os.path.join(root, file))

    return md_files


def fix_line_with_quote_after_bullet(line, str_to_replace: str="$QUOTETOBEREPLACED$", str_replacement: str=">"):

    double_quote = str_to_replace + ' ' + str_to_replace
    double_quote_out = str_replacement + ' ' + str_replacement
    line_fixed = line.replace('- ' + double_quote, double_quote_out + ' -')
    line_fixed = line_fixed.replace('- ' + str_to_replace, str_replacement + ' -')

    return line_fixed


def fix_line_with_quote_after_numbering(line, str_to_replace, str_replacement):

    number = line.split('.')[0]

    double_quote = str_to_replace + ' ' + str_to_replace
    double_quote_out = str_replacement + ' ' + str_replacement
    line_fixed = line.replace(f'{number}. ' + double_quote, double_quote_out + f' {number}.')
    line_fixed = line_fixed.replace(f'{number}. ' + str_to_replace, str_replacement + f' {number}.')

    return line_fixed


def replace_quote_to_markdown_quote(lines, str_to_replace: str="$QUOTETOBEREPLACED$", str_replacement: str=">"):

    lines_out = []
    check_following_line = False
    for i, line in enumerate(lines):

        # line = ' '.join(line.split())  # convert possible NBSP to space

        if line == "\n":
            if check_following_line:
                # remove the extra line break, if there was a quote line break on previous line
                # remove only between quotes, not after the last quote
                if str_to_replace not in lines[i + 1]:
                    lines_out.append(line)
                check_following_line = False
            else:
                lines_out.append(line)
        else:
            if str_to_replace in line:
                check_following_line = True
                if line != '$QUOTETOBEREPLACED$\n':
                    # skip line breaks leading to quotes with no text
                    if line.startswith('- '):
                        # here the quote might be after the bullet point, should be before
                        line_fix = fix_line_with_quote_after_bullet(line, str_to_replace, str_replacement)
                        lines_out.append(line_fix)
                    elif line[0].isdigit():
                        line_fix = fix_line_with_quote_after_numbering(line, str_to_replace, str_replacement)
                        lines_out.append(line_fix)
                    else:
                        lines_out.append(line.replace(str_to_replace, str_replacement))

            else:
                lines_out.append(line)

    return lines_out


def find_style_matches(line_out, replacement):

    candidates = line_out.split(replacement)
    styles_matched = []
    for i, candidate in enumerate(candidates):
        string_to_find = replacement + candidate.strip() + replacement

        if string_to_find in line_out:
            styles_matched.append(string_to_find)

    return styles_matched


def check_for_need_of_whitespace(char: str):
    if char != ' ' and char != '-' and char != '.' and char != ',':
        return True
    else:
        return False


def check_surrounding(line_out, styling, replacement):

    start_idx = line_out.find(styling)
    line_out2 = line_out
    if start_idx != -1:
        try:
            end_idx = start_idx + len(styling)
            char_before = line_out[start_idx - 1]
            char_after = line_out[end_idx]
            if check_for_need_of_whitespace(char=char_before):
                # add whitespace before
                before = line_out2[:start_idx]
                after = line_out2[start_idx:]
                line_out2 = before + ' ' + after
            if check_for_need_of_whitespace(char=char_after):
                # add whitespace after
                before = line_out2[:end_idx]
                after = line_out2[end_idx:]
                # quick n dirty fix for now, not sure why this happens
                if after.startswith(replacement[0]):
                    after = after[1:]
                    before += replacement[0]
                line_out2 = before + ' ' + after
        except IndexError:
            logging.debug(f"IndexError: {line_out}")

    return line_out2

def add_whitespaces_around_words(line_out, replacement):

    styles_matched = find_style_matches(line_out, replacement)

    for styling in styles_matched:
        line_out = check_surrounding(line_out, styling, replacement)

    return line_out


def replace_chars(lines, to_replace: str="****", replacement: str="**", whitespace: bool=True):

    lines_out = []
    for i, line in enumerate(lines):
        if to_replace in line:
            line_out = line.replace(to_replace, replacement)
            if whitespace:
                line_out = add_whitespaces_around_words(line_out, replacement)
        else:
            line_out = line
        lines_out.append(line_out)

    return lines_out


def fix_markdown_hyperlinks(lines):

    lines_out = []
    fixes = []

    # sometimes you get [[Author et al. (2023)](doi.org/101012)] instead of [Author et al. (2023)](doi.org/101012)
    # you should remove the extra brackets, check "_devel_test.md"

    return lines_out, fixes


def replace_empty_quotes(lines):

    lines_out = []
    for i, line in enumerate(lines):

        if i > 0 and i < len(lines) - 1:
            prev_line = lines[i - 1]
            next_line = lines[i + 1]
            if '>\n' in line:
                b = 1
            elif '>\n' in prev_line and line == '\n':
                c = 1
            else:
                lines_out.append(line)

    return lines_out


def process_md_lines(lines: list,
                     replace_ops: bool = True,
                     fix_hyperlinks: bool = False):

    lines_out2 = lines
    if replace_ops:
        # replace $QUOTETOBEREPLACED$ with markdown quotesi
        lines_out2 = replace_quote_to_markdown_quote(lines_out2)
        lines_out2 = replace_empty_quotes(lines_out2)

        lines_out2 = replace_chars(lines_out2, to_replace="****", replacement="**")
        lines_out2 = replace_chars(lines_out2, to_replace="***", replacement="**")
        lines_out2 = replace_chars(lines_out2, to_replace="====", replacement="==")
        lines_out2 = replace_chars(lines_out2, to_replace="===", replacement="==")

        # orphan styling, parsing errors:
        lines_out2 = replace_chars(lines_out2, to_replace="**== **", replacement="", whitespace=False)
        lines_out2 = replace_chars(lines_out2, to_replace="** **", replacement="", whitespace=False)
        lines_out2 = replace_chars(lines_out2, to_replace="==**==", replacement="", whitespace=False)
        lines_out2 = replace_chars(lines_out2, to_replace="==** ==**", replacement="", whitespace=False)
        lines_out2 = replace_chars(lines_out2, to_replace="**==** ==", replacement=" ", whitespace=False)
        lines_out2 = replace_chars(lines_out2, to_replace="**_**", replacement=" ", whitespace=False)
        lines_out2 = replace_chars(lines_out2, to_replace="*_**_", replacement=" ", whitespace=False)
        lines_out2 = replace_chars(lines_out2, to_replace="_ **_*", replacement=" ", whitespace=False)
        lines_out2 = replace_chars(lines_out2, to_replace="*_ **_==**", replacement=" ", whitespace=False)
        lines_out2 = replace_chars(lines_out2, to_replace="_*].*_** _==", replacement=" ", whitespace=False)
        lines_out2 = replace_chars(lines_out2, to_replace="_*].*_** _==", replacement=" ", whitespace=False)
        lines_out2 = replace_chars(lines_out2, to_replace="*==_**_ **", replacement=" ", whitespace=False)
        lines_out2 = replace_chars(lines_out2, to_replace="*_**_*", replacement=" ", whitespace=False)

    if fix_hyperlinks:
        #lines_out2, fixes = fix_markdown_hyperlinks(lines_out2)
        a = 1


    return lines_out2


def process_md_file(md_file):

    with open(md_file, "r") as f:
        lines = f.readlines()

    lines = process_md_lines(lines)

    # export as markdown document
    shutil.copy(md_file, md_file + ".bak")
    with open(md_file, "w") as f:
        f.writelines(lines)


if __name__ == "__main__":

    logging.basicConfig(level=logging.INFO)
    args = parse_args_to_dict()

    md_files = get_import_markdowns(args["input_folder"])

    for md_file in md_files:
        logging.info(f"Processing {md_file}")
        process_md_file(md_file)