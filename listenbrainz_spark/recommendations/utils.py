import os

from jinja2 import Environment, FileSystemLoader

HTML_FILES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'html_files')


def save_html(filename, context, template):
    path = os.path.dirname(os.path.abspath(__file__))
    template_environment = Environment(loader=FileSystemLoader(os.path.join(path, 'templates')))

    if not os.path.isdir(HTML_FILES_PATH):
        os.mkdir(HTML_FILES_PATH)

    outputfile = os.path.join(HTML_FILES_PATH, filename)
    with open(outputfile, 'w') as f:
        html = template_environment.get_template(template).render(context)
        f.write(html)
