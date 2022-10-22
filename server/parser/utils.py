import os

DEBUG = True


def traverse_dir_files(root_dir, ext=None):
    names_list = []
    paths_list = []
    for parent, _, fileNames in os.walk(root_dir):
        for name in fileNames:
            if name.startswith("."):
                continue
            if ext:
                if name.endswith(tuple(ext)):
                    names_list.append(name)
                    paths_list.append(os.path.join(parent, name))
            else:
                names_list.append(name)
                paths_list.append(os.path.join(parent, name))
    if not names_list:
        return paths_list, names_list
    return paths_list, names_list


def printlog(*args, **kwargs):
    global DEBUG
    if DEBUG:
        print("----LOG----", *args, **kwargs)
    else:
        pass
