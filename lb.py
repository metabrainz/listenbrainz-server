#!/usr/bin/env python3
"""
ListenBrainz CLI - Unified command-line interface for development tasks

This tool provides a consistent, cross-platform interface for common
development operations, wrapping docker-compose and management commands.

Usage:
    lb init                 # Initialize databases and setup
    lb start                # Start development environment
    lb stop                 # Stop all containers
    lb test [OPTIONS]       # Run tests
    lb db psql              # Open PostgreSQL shell
    lb db timescale         # Open TimescaleDB shell
    lb logs [SERVICE]       # View container logs
    lb clean                # Clean up containers and volumes
    lb manage [COMMAND]     # Run management commands
"""

import os
import sys
import platform
import subprocess
import click
from pathlib import Path


# Color output for better UX
class Colors:
    """ANSI color codes for terminal output"""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def print_success(msg):
    """Print success message in green"""
    click.echo(f"{Colors.OKGREEN}✓{Colors.ENDC} {msg}")


def print_error(msg):
    """Print error message in red"""
    click.echo(f"{Colors.FAIL}✗{Colors.ENDC} {msg}", err=True)


def print_info(msg):
    """Print info message in cyan"""
    click.echo(f"{Colors.OKCYAN}ℹ{Colors.ENDC} {msg}")


def print_warning(msg):
    """Print warning message in yellow"""
    click.echo(f"{Colors.WARNING}⚠{Colors.ENDC} {msg}")


def get_docker_compose_cmd():
    """Detect and return the appropriate docker-compose command"""
    try:
        subprocess.run(
            ["docker", "compose", "version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )
        return ["docker", "compose"]
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ["docker-compose"]


def run_command(cmd, shell=False, check=True, env=None):
    """Execute a command and handle errors"""
    try:
        if shell and isinstance(cmd, list):
            cmd = ' '.join(cmd)
        
        result = subprocess.run(
            cmd,
            shell=shell,
            check=check,
            env=env or os.environ.copy()
        )
        return result.returncode
    except subprocess.CalledProcessError as e:
        print_error(f"Command failed with exit code {e.returncode}")
        return e.returncode
    except FileNotFoundError:
        print_error(f"Command not found: {cmd[0] if isinstance(cmd, list) else cmd}")
        return 1


def ensure_repo_root():
    """Ensure we're running from the repository root"""
    if not os.path.isdir("docker"):
        print_error("This command must be run from the listenbrainz-server root directory")
        sys.exit(1)


def ensure_env_file():
    """Ensure .env file exists with required variables"""
    if not os.path.exists(".env"):
        print_info("Creating .env file...")
        with open(".env", "w") as f:
            if platform.system() != "Windows":
                import pwd
                uid = os.getuid()
                gid = os.getgid()
                f.write(f"LB_DOCKER_USER={uid}\n")
                f.write(f"LB_DOCKER_GROUP={gid}\n")
            else:
                # Windows doesn't need these
                f.write("# Environment file for ListenBrainz development\n")
        print_success("Created .env file")


@click.group(invoke_without_command=True)
@click.pass_context
@click.option('--version', is_flag=True, help='Show version information')
def cli(ctx, version):
    """
    ListenBrainz CLI - Unified development tool
    
    A cross-platform command-line interface for managing ListenBrainz
    development environment, tests, and common tasks.
    """
    if version:
        click.echo("ListenBrainz CLI v1.0.0")
        ctx.exit()
    
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@cli.command()
@click.option('--skip-db', is_flag=True, help='Skip database initialization')
def init(skip_db):
    """
    Initialize ListenBrainz development environment
    
    This command:
    - Creates .env file if needed
    - Builds Docker containers
    - Initializes PostgreSQL and TimescaleDB databases
    """
    ensure_repo_root()
    ensure_env_file()
    
    print_info("Initializing ListenBrainz development environment...")
    
    # Build containers
    print_info("Building Docker containers (this may take a while)...")
    docker_compose = get_docker_compose_cmd()
    
    result = run_command(
        docker_compose + ["-f", "docker/docker-compose.yml", "-p", "listenbrainz", "build"]
    )
    
    if result != 0:
        print_error("Failed to build containers")
        sys.exit(result)
    
    print_success("Containers built successfully")
    
    if not skip_db:
        # Initialize databases
        print_info("Initializing databases...")
        
        # Start database containers
        run_command(
            docker_compose + [
                "-f", "docker/docker-compose.yml",
                "-p", "listenbrainz",
                "up", "-d", "lb_db", "redis"
            ]
        )
        
        # Wait and initialize
        init_cmd = (
            docker_compose + [
                "-f", "docker/docker-compose.yml",
                "-p", "listenbrainz",
                "run", "--rm", "web",
                "bash", "-c",
                "python3 manage.py init_db --create-db && python3 manage.py init_ts_db --create-db"
            ]
        )
        
        result = run_command(init_cmd)
        
        if result != 0:
            print_error("Failed to initialize databases")
            sys.exit(result)
        
        print_success("Databases initialized successfully")
    
    print_success("ListenBrainz development environment is ready!")
    print_info("Run 'lb start' to start the development server")


@cli.command()
@click.option('-d', '--detach', is_flag=True, help='Run in detached mode')
def start(detach):
    """
    Start ListenBrainz development environment
    
    Starts all required Docker containers. By default runs in foreground
    (use Ctrl+C to stop). Use -d flag to run in background.
    """
    ensure_repo_root()
    ensure_env_file()
    
    print_info("Starting ListenBrainz development environment...")
    docker_compose = get_docker_compose_cmd()
    
    cmd = docker_compose + [
        "-f", "docker/docker-compose.yml",
        "-p", "listenbrainz",
        "--env-file", ".env",
        "up"
    ]
    
    if detach:
        cmd.append("-d")
        result = run_command(cmd)
        if result == 0:
            print_success("ListenBrainz started in background")
            print_info("Visit http://localhost:8100 in your browser")
            print_info("Run 'lb logs' to view logs")
    else:
        print_info("Starting in foreground mode (press Ctrl+C to stop)...")
        print_info("Visit http://localhost:8100 in your browser")
        result = run_command(cmd)
    
    sys.exit(result)


@cli.command()
def stop():
    """
    Stop all ListenBrainz containers
    
    Gracefully stops all running containers without removing them.
    Use 'lb clean' to remove containers and volumes.
    """
    ensure_repo_root()
    
    print_info("Stopping ListenBrainz containers...")
    docker_compose = get_docker_compose_cmd()
    
    result = run_command(
        docker_compose + [
            "-f", "docker/docker-compose.yml",
            "-p", "listenbrainz",
            "stop"
        ]
    )
    
    if result == 0:
        print_success("Containers stopped successfully")
    else:
        print_error("Failed to stop containers")
    
    sys.exit(result)


@cli.command()
@click.option('--build', '-b', is_flag=True, help='Rebuild containers before testing')
@click.option('--type', '-t', 
              type=click.Choice(['unit', 'frontend', 'spark'], case_sensitive=False),
              default='unit',
              help='Type of tests to run')
@click.argument('pytest_args', nargs=-1)
def test(build, type, pytest_args):
    """
    Run tests
    
    Examples:
        lb test                              # Run all unit tests
        lb test --build                      # Rebuild and test
        lb test --type frontend              # Run frontend tests
        lb test listenbrainz/tests/test.py  # Run specific test file
    """
    ensure_repo_root()
    
    if platform.system() == "Windows":
        # On Windows, call test.sh through WSL or use Python subprocess
        print_warning("Running tests through test.sh...")
        if build:
            result = run_command(["bash", "test.sh", "-b"], shell=False)
        else:
            cmd = ["bash", "test.sh"]
            if pytest_args:
                cmd.extend(pytest_args)
            result = run_command(cmd, shell=False)
    else:
        # On Unix-like systems, call test.sh directly
        cmd = ["./test.sh"]
        if build:
            cmd.append("-b")
        if type == 'frontend':
            cmd.append("frontend")
        elif type == 'spark':
            cmd.append("spark")
        
        if pytest_args:
            cmd.extend(pytest_args)
        
        result = run_command(cmd, shell=False)
    
    sys.exit(result)


@cli.group()
def db():
    """Database management commands"""
    pass


@db.command('psql')
def db_psql():
    """
    Open PostgreSQL shell for main ListenBrainz database
    
    Connects to the main PostgreSQL database where user data,
    playlists, and other metadata is stored.
    """
    ensure_repo_root()
    ensure_env_file()
    
    print_info("Connecting to PostgreSQL...")
    docker_compose = get_docker_compose_cmd()
    
    result = run_command(
        docker_compose + [
            "-f", "docker/docker-compose.yml",
            "-p", "listenbrainz",
            "--env-file", ".env",
            "run", "--rm", "web",
            "psql", "postgresql://listenbrainz:listenbrainz@lb_db/listenbrainz"
        ]
    )
    
    sys.exit(result)


@db.command('timescale')
def db_timescale():
    """
    Open TimescaleDB shell for listens data
    
    Connects to the TimescaleDB database where user listens
    (time-series data) is stored.
    """
    ensure_repo_root()
    ensure_env_file()
    
    print_info("Connecting to TimescaleDB...")
    docker_compose = get_docker_compose_cmd()
    
    result = run_command(
        docker_compose + [
            "-f", "docker/docker-compose.yml",
            "-p", "listenbrainz",
            "--env-file", ".env",
            "run", "--rm", "web",
            "psql", "postgresql://listenbrainz_ts:listenbrainz_ts@lb_db/listenbrainz_ts"
        ]
    )
    
    sys.exit(result)


@cli.command()
@click.argument('service', required=False)
@click.option('-f', '--follow', is_flag=True, help='Follow log output')
@click.option('-n', '--tail', type=int, default=100, help='Number of lines to show')
def logs(service, follow, tail):
    """
    View container logs
    
    Examples:
        lb logs              # Show logs from all services
        lb logs web          # Show logs from web service
        lb logs -f           # Follow logs (like tail -f)
        lb logs web -n 50    # Show last 50 lines from web
    """
    ensure_repo_root()
    
    docker_compose = get_docker_compose_cmd()
    
    cmd = docker_compose + [
        "-f", "docker/docker-compose.yml",
        "-p", "listenbrainz",
        "logs",
        f"--tail={tail}"
    ]
    
    if follow:
        cmd.append("-f")
    
    if service:
        cmd.append(service)
    
    result = run_command(cmd)
    sys.exit(result)


@cli.command()
@click.option('--volumes', '-v', is_flag=True, help='Also remove volumes')
@click.confirmation_option(prompt='This will remove all containers and optionally volumes. Continue?')
def clean(volumes):
    """
    Clean up Docker containers and optionally volumes
    
    WARNING: This will stop and remove all ListenBrainz containers.
    Use --volumes flag to also remove data volumes (databases will be lost).
    """
    ensure_repo_root()
    
    print_info("Cleaning up ListenBrainz containers...")
    docker_compose = get_docker_compose_cmd()
    
    cmd = docker_compose + [
        "-f", "docker/docker-compose.yml",
        "-p", "listenbrainz",
        "down"
    ]
    
    if volumes:
        cmd.append("-v")
        print_warning("Removing volumes - all database data will be lost!")
    
    result = run_command(cmd)
    
    if result == 0:
        print_success("Cleanup completed successfully")
    else:
        print_error("Cleanup failed")
    
    sys.exit(result)


@cli.command()
def bash():
    """
    Open bash shell in web container
    
    Provides direct shell access to the web service container
    for debugging and manual operations.
    """
    ensure_repo_root()
    ensure_env_file()
    
    print_info("Opening bash shell in web container...")
    docker_compose = get_docker_compose_cmd()
    
    result = run_command(
        docker_compose + [
            "-f", "docker/docker-compose.yml",
            "-p", "listenbrainz",
            "--env-file", ".env",
            "run", "--rm", "web", "bash"
        ]
    )
    
    sys.exit(result)


@cli.command()
def shell():
    """
    Open Flask shell with ListenBrainz app context
    
    Starts an interactive Python shell with the Flask application
    loaded, useful for testing models and database operations.
    """
    ensure_repo_root()
    ensure_env_file()
    
    print_info("Opening Flask shell...")
    docker_compose = get_docker_compose_cmd()
    
    result = run_command(
        docker_compose + [
            "-f", "docker/docker-compose.yml",
            "-p", "listenbrainz",
            "--env-file", ".env",
            "run", "--rm", "web", "flask", "shell"
        ]
    )
    
    sys.exit(result)


@cli.command(context_settings=dict(ignore_unknown_options=True))
@click.argument('manage_args', nargs=-1)
def manage(manage_args):
    """
    Run manage.py commands
    
    Examples:
        lb manage --help                    # Show all management commands
        lb manage init_db --create-db       # Initialize database
        lb manage dump create_full          # Create database dump
    """
    ensure_repo_root()
    ensure_env_file()
    
    if not manage_args:
        print_error("No management command specified")
        print_info("Run 'lb manage --help' to see available commands")
        sys.exit(1)
    
    print_info(f"Running manage.py {' '.join(manage_args)}...")
    docker_compose = get_docker_compose_cmd()
    
    result = run_command(
        docker_compose + [
            "-f", "docker/docker-compose.yml",
            "-p", "listenbrainz",
            "--env-file", ".env",
            "run", "--rm", "web",
            "python3", "manage.py"
        ] + list(manage_args)
    )
    
    sys.exit(result)


@cli.command()
def status():
    """
    Show status of all ListenBrainz containers
    
    Displays which containers are running, stopped, or missing.
    """
    ensure_repo_root()
    
    print_info("ListenBrainz container status:")
    docker_compose = get_docker_compose_cmd()
    
    result = run_command(
        docker_compose + [
            "-f", "docker/docker-compose.yml",
            "-p", "listenbrainz",
            "ps"
        ]
    )
    
    sys.exit(result)


@cli.command()
@click.option('--service', '-s', help='Service to restart')
def restart(service):
    """
    Restart containers
    
    Examples:
        lb restart           # Restart all services
        lb restart -s web    # Restart only web service
    """
    ensure_repo_root()
    
    docker_compose = get_docker_compose_cmd()
    
    cmd = docker_compose + [
        "-f", "docker/docker-compose.yml",
        "-p", "listenbrainz",
        "restart"
    ]
    
    if service:
        cmd.append(service)
        print_info(f"Restarting {service}...")
    else:
        print_info("Restarting all services...")
    
    result = run_command(cmd)
    
    if result == 0:
        print_success("Restart completed")
    else:
        print_error("Restart failed")
    
    sys.exit(result)


if __name__ == '__main__':
    cli()
