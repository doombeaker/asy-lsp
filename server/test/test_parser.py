import unittest

from ..parser.ast import FileParsed
from ..parser.utils import traverse_dir_files

def run_parser(file_path):
    file = FileParsed(file_path)
    file.parse()
    jumptable = file.construct_jump_table()

class TestParser(unittest.TestCase):

    def test_parser(self):
        import os
        asy_files_root = os.path.join(os.path.dirname(__file__), 'asyfiles')
        file_paths, _ = traverse_dir_files(asy_files_root, ext='.asy')
        for file_path in file_paths:
            print(f"Testing {file_path}")
            run_parser(file_path)

if __name__ == '__main__':
    unittest.main()
