import os
import unittest

class UtilsTestCase(unittest.TestCase):

    def test_html_dir_exists(self):
        html_files_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'html_files')
        dir_exists = os.path.isdir(html_files_path)
        self.assertTrue(dir_exists)
