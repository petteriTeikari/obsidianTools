import argparse
import itertools
import logging
import os


def parse_args_to_dict():

    parser = argparse.ArgumentParser(
        description="Convert Markdown (.md) files from Obsidian with Zotero Integration (Better BibTeX) "
                    "keys to hardcoded hyperlinks"
    )
    parser.add_argument(
        "-i",
        "--input-folder",
        type=str,
        required=True,
        default="/home/petteri/Downloads/test_parsing",
        help="Where is / are your html files located?",
    )

    args_dict = vars(parser.parse_args())

    return args_dict


def get_import_htmls(base_folder: str) -> list:
    import os

    html_files = []
    for root, dirs, files in os.walk(base_folder):
        for file in files:
            if file.endswith(".html"):
                html_files.append(os.path.join(root, file))

    return html_files


def split_head_and_body(html_file: str, add_removed_tags_back: bool = True) -> tuple:

    with open(html_file, "r") as f:
        html = f.read()

    head = html.split("<head>")[1].split("</head>")[0]
    body = html.split("</head>")[1].split("</html>")[0]

    if add_removed_tags_back:
        # you want to add the extra "==" markdown tags and keep rest of the html as it is
        # so that the Obsidian Importer can import the Google Docs export with the highlighting
        head = "<html><head>" + head + "</head>"
        body = body + "</html>"

    return head, body


def filter_head_with_substring(head_lines: list, substring: str) -> list:

    filtered_head_lines = []
    for line in head_lines:
        if substring in line:
            filtered_head_lines.append(line)

    return filtered_head_lines


def parse_highlight_class_names(head_lines: list, exclude_str: str = 'background-color:#ffffff') -> list:

    class_names = []
    for line in head_lines:
        fields = line.split(".")
        for field in fields:
            if 'background-color' in field:
                if exclude_str not in field:
                    try:
                        class_name, class_attr = field.split("{")
                        class_attr = class_attr.split("}")[0]
                        attr_name, color_value = class_attr.split(":")
                        # double-check that the parsing makes sense
                        if attr_name == 'background-color' and color_value != '#ffffff':
                            class_names.append((class_name, color_value))
                        else:
                            logging.warning(f"Unexpected attribute name {attr_name} or color value {color_value}")
                    except ValueError:
                        logging.debug(f"ValueError: {field}")

    return class_names


def parse_class_names(head_lines: list,
                      substring: str = 'font-style',
                      exclude_str: str = 'font-style:normal') -> list:

    class_names = []
    for line in head_lines:
        if substring in line:
            if exclude_str not in line:
                class_name, class_attr = line.split("{")
                class_name = class_name.replace(".", "")
                class_attr_str = class_attr.split("}")[0]
                class_attrs = class_attr_str.split(";")
                for class_attr in class_attrs:
                    if substring in class_attr:
                        if not class_name.startswith("h"): # ignore header, h6 especially
                            attr_name, attr_value = class_attr.split(":")
                            class_names.append((class_name, attr_value))

    return class_names


def find_classes_with_background_color(head: str,
                                       substring: str = "background-color",
                                       exclude_str: str = None) -> list:

    if substring == 'background-color':
        head_lines = head.split(";")
        head_lines = filter_head_with_substring(head_lines, substring=substring)
        class_names = parse_highlight_class_names(head_lines, exclude_str=exclude_str)

    else:
        head_lines = head.split("}")
        head_lines = filter_head_with_substring(head_lines, substring=substring)
        class_names = parse_class_names(head_lines, substring=substring, exclude_str=exclude_str)

    return class_names


def split_by_str(body, substring: str = '<span ') -> list:
    return body.split(substring)


# def make_sure_of_a_space_after_string(body, output_str):
#     before, after = body.split(output_str)
#     fields = after.split('>')
#     first_tag = fields[0]
#     first_string = fields[1]
#     first_string2 = first_string
#     if not first_string.startswith(' '):
#         if not first_string.startswith('<'):
#             first_string2 = ' ' + first_string
#
#     body_out = body.replace(first_string, first_string2)
#
#     return body_out


def clean_text_in_span(text_in_span: str) -> str:
    text_in_span_wo_whitespace = text_in_span.strip()
    text_in_span_wo_whitespace = text_in_span_wo_whitespace.replace('&nbsp;', '')
    text_in_span_wo_whitespace = text_in_span_wo_whitespace.replace('&ldquo;', '"')
    text_in_span_wo_whitespace = text_in_span_wo_whitespace.replace('&rdquo;', '"')

    return text_in_span_wo_whitespace


def fix_single_class_use(body, class_name, styling: str = '=='):

    fixes = []
    fields = split_by_str(body, '<span ')
    for field in fields:
        if field.startswith('class'):
            # note you can have multiple classes in one span tag
            class_names_in_text: list = field.split('class="')[1].split('"')[0].split(" ")
            class_str: str = ' '.join(class_names_in_text)
            text_in_span = field.split('class="')[1].split('"')[1].split('</span>')[0].split('>')[1]
            if not text_in_span == '':
                # do not add styling if there is no text in the span tag
                if not text_in_span.startswith('<a'):
                    # do not apply on hyperlinks
                    text_in_span_wo_whitespace = clean_text_in_span(text_in_span)
                    if class_name in class_names_in_text:
                        input_str = f'<span class="{class_str}">{text_in_span}</span>'
                        output_str = f'<span class="{class_str}">{styling}{text_in_span_wo_whitespace}{styling}</span>'
                        body = body.replace(input_str, output_str)
                        # body = make_sure_of_a_space_after_string(body, output_str)
                        fixes.append((input_str, output_str))

    return body, fixes


def get_unique_paragraph_class_tags(body: str, class_name: str, class_divider: str = '<p ',
                                    attr_value: str = '36pt') -> list:

    input_strings = []
    fields = split_by_str(body, class_divider)

    for field in fields:
        if field.startswith('class'):
            # note you can have multiple classes in one span tag
            class_names_in_text: list = field.split('class="')[1].split('"')[0].split(" ")
            class_str: str = ' '.join(class_names_in_text)
            text_in_span = field.split('class="')[1:]

            try:
                text_in_span = ''.join(text_in_span).split('<span ')[1].split('">')[1]

                if class_name in class_names_in_text:
                    input_str = f'{class_divider}class="{class_str}">'
                    input_strings.append((input_str, attr_value))
            except IndexError:
                logging.debug(f"IndexError: {text_in_span}")

    input_strings_unique = list(set(input_strings))


    return input_strings_unique


def fix_single_class_use_paragraph(body, class_name, class_tags: list):

    fixes = []
    for class_tag, margin in class_tags:
        if margin == '36pt':
            output_str = f'{class_tag}$QUOTETOBEREPLACED$ ' # you need to manally replace this with ">" in Obsidian
        elif margin == '72pt':
            output_str = f'{class_tag}$QUOTETOBEREPLACED$ $QUOTETOBEREPLACED$ '
        else:
            raise NotImplementedError('Petteri was using only 36 and 72pt margins')
        body = body.replace(class_tag, output_str)
        fixes.append((class_tag, output_str))

    return body, fixes


def fix_class_uses_from_body(body: str,
                             class_names: list,
                             styling: str = '==') -> str:

    fixes_body = []
    for class_name, attr_value in class_names:
        body, fixes = fix_single_class_use(body, class_name, styling=styling)
        fixes_body += fixes

    return body, fixes_body


def fix_indented_margins_for_quotes(body: str, class_names: list,
                                    accepted_margins=['36pt']) -> str:

    # Get unique paragraph class tags "c5", "c5 c8", "c5 c31 c73" etc.
    class_tags = []
    class_dividers = ['<p ', '<li ']
    accepted_margins = (['36pt', '72pt'], ['36pt', '72pt'])

    for (class_divider, margins_ok) in zip(class_dividers, accepted_margins):
        for class_name, attr_value in class_names:
            if attr_value in margins_ok:
                logging.debug(f"Processing {class_name} with {attr_value}")
                class_tags += get_unique_paragraph_class_tags(body, class_name, class_divider, attr_value)

    body, fixes = fix_single_class_use_paragraph(body, class_name, class_tags)

    return body


def process_html(html_file: str,
                 fix_bold: bool = True,
                 fix_italic: bool = True,
                 fix_highlight: bool = True,
                 fix_tab: bool = True,
                 fix_indented_margin: bool = True):

    head, body = split_head_and_body(html_file)
    fixes = {}

    if fix_highlight:
        class_names = find_classes_with_background_color(head,
                                                         substring='background-color',
                                                         exclude_str='background-color:#ffffff')
        body, fixes['highlight'] = fix_class_uses_from_body(body,
                                                         class_names,
                                                         styling = '==')

    if fix_italic:
        class_names = find_classes_with_background_color(head,
                                                         substring='font-style',
                                                         exclude_str='font-style:normal')
        body, fixes['italic'] = fix_class_uses_from_body(body,
                                                      class_names,
                                                      styling = '_')

    if fix_bold:
        class_names = find_classes_with_background_color(head,
                                                         substring='font-weight', # 700 for bold
                                                         exclude_str='font-weight:400')
        body, fixes['bold'] = fix_class_uses_from_body(body,
                                                    class_names,
                                                    styling = '**')

    if fix_tab:
        a = 'placeholder'

    if fix_indented_margin:
        class_names = find_classes_with_background_color(head,
                                                         substring='margin-left',  # 36px for indented
                                                         exclude_str='bullet')
        body = fix_indented_margins_for_quotes(body, class_names)

    return head+body, fixes


def export_html(html: str, html_file: str):

    # create backup of the original html file
    os.rename(html_file, html_file.replace(".html", "_backup.html"))

    with open(html_file, "w") as f:
        f.write(html)


if __name__ == "__main__":

    logging.basicConfig(level=logging.INFO)
    args = parse_args_to_dict()

    html_files = get_import_htmls(args["input_folder"])

    for html_file in html_files:
        logging.info(f"Processing {html_file}")
        html, fixes = process_html(html_file)
        export_html(html, html_file)
