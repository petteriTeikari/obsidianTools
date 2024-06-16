import logging
import re


def get_image_refs_of_line(line):

    line = line.replace('> ', '').replace('>', '')

    #pattern1 = '!\[.*\]\(.*.\)'
    pattern2 = r'!\[\[\D*\d*\.\D{3,4}]]' # https://stackoverflow.com/q/68813348
    pattern3 = '!\[[^\]]*\]\((.*?)\s*("(?:.*[^"])")?\s*\)' # https://stackoverflow.com/a/44227600

    #match1 = [x.group() for x in re.finditer(pattern1, line)]
    match2 = [x.group() for x in re.finditer(pattern2, line)]
    match3 = [x.group() for x in re.finditer(pattern3, line)]
    matches = match2 + match3
    image_paths = return_image_paths(matches)

    if image_paths is not None:
        return image_paths
    else:
        return None


def return_image_paths(matches):

    image_paths = []
    for ms in matches:
        if ms is not None:
            if '![[' in ms:
                image_path = ms.split('[[')[1].split(']]')[0]
                image_paths.append(image_path)
            else:
                image_path = ms.split('](')[1].split(')')[0]
                image_paths.append(image_path)

    if len(image_paths) > 0:
        return image_paths
    else:
        return None


def get_absolute_img_path(ref, img_files):

    ref = ref.replace(' ', '%20')
    res = [i for i in img_files if ref in i]
    if len(res) > 0:
        if len(res) == 1:
            return res
        else:
            # TODO! You could either have the same exact image in different folders,
            #  or you could have non-unique filenames
            return res
    else:
        return None