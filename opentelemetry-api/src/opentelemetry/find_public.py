from os import walk
from os.path import join
from re import match


for root, _, files in walk("."):
    for file_ in files:
        if file_.endswith(".py"):
            file_path = join(root, file_)
            print(file_path)
            with open(file_path) as the_file:
                for line in the_file.readlines():
                    the_match = match(r"((def|class) [^_]\w+)", line)
                    if the_match is not None:
                        print(f"    {the_match.group(1)}")
