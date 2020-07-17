import os

from jinja2 import Environment, FileSystemLoader

HTML_FILES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'html_files')

def save_html(filename, context, template):
    path = os.path.dirname(os.path.abspath(__file__))
    template_environment = Environment(
    loader=FileSystemLoader(os.path.join(path, 'templates')))
    outputfile = os.path.join(HTML_FILES_PATH, filename)
    with open(outputfile, 'w') as f:
        html = template_environment.get_template(template).render(context)
        f.write(html)

def check_html_files_dir_path():
    dir_exists = os.path.isdir(HTML_FILES_PATH)
    return dir_exists
