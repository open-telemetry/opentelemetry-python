from json import dumps
from os import getcwd, walk
from os.path import join
from re import match

parsed_files = {}

for dirpath, dirnames, filenames in walk(getcwd()):

    dirnames_to_remove = []

    for dirname in ["opentelemetry-python-contrib", "docs", "scripts"]:

        if dirname in dirnames:
            dirnames_to_remove.append(dirname)

    for dirname in dirnames:
        if (
            dirname.startswith(".") or
            dirname.endswith("tests") or
            dirname.endswith("examples") or
            dirname.endswith("gen")
        ):
            dirnames_to_remove.append(dirname)

    for dirname_to_remove in dirnames_to_remove:
        dirnames.remove(dirname_to_remove)

    filenames_to_remove = []

    for filename in filenames:

        if not filename.endswith(".py") or "pb2" in filename:
            filenames_to_remove.append(filename)

    for filename_to_remove in filenames_to_remove:
        filenames.remove(filename_to_remove)

    if filenames:

        for filename in filenames:

            public_symbols = []

            file_path = join(dirpath, filename)

            with open(file_path) as file_:
                for line in file_.readlines():

                    symbol = r"[a-zA-Z][_\w]+"

                    matching_line = match(
                        r"({symbol})\s=\s.+|"
                        r"def\s({symbol})|"
                        r"class\s({symbol})".format(symbol=symbol),
                        line
                    )

                    if matching_line is not None:

                        public_symbols.append(
                            next(filter(bool, matching_line.groups()))
                        )

        if public_symbols:
            parsed_files[file_path] = public_symbols

print(dumps(parsed_files, indent=4))
