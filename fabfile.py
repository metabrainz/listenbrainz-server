from fabric.api import local
from fabric.colors import green

def git_pull():
    local("git pull origin")
    print((green("Updated local code.", bold=True)))


def install_requirements():
    local("pip install -r requirements.txt")
    print((green("Installed requirements.", bold=True)))


def compile_styling():
    """Compile main.less into main.css.
    This command requires Less (CSS pre-processor). More information about it can be
    found at http://lesscss.org/.
    """
    style_path = "webserver/static/css/"
    local("lessc --clean-css %smain.less > %smain.css" % (style_path, style_path))
    print((green("Style sheets have been compiled successfully.", bold=True)))


def deploy():
    git_pull()
    install_requirements()
    compile_styling()
