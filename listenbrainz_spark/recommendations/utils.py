import os 
from jinja2 import Environment, FileSystemLoader

def save_html(filename, context, template):
    path = os.path.dirname(os.path.abspath(__file__))
    template_environment = Environment(
    loader=FileSystemLoader(os.path.join(path, 'templates')))
    outputfile = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
    with open(outputfile, 'w') as f:
        html = template_environment.get_template(template).render(context)
        f.write(html)