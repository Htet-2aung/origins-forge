import json
import typer
import os
import shutil
import subprocess
import secrets
import requests
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.progress import track
from rich.table import Table
from rich.markdown import Markdown
from openai import OpenAI
import platform
import sys


app = typer.Typer(help="Origins Intelligent Dev Tool v3.0")
console = Console()

CLI_ROOT = os.path.dirname(os.path.abspath(__file__))
PROJECTS_DIR = os.path.join(CLI_ROOT, "projects")
CONFIG_DIR = os.path.expanduser("~/.origins")
CACHE_DIR = os.path.join(CONFIG_DIR, "cache")
MANIFEST_FILE = os.path.join(CONFIG_DIR, "templates.json")
MANIFEST_URL = "https://gist.github.com/Htet-2aung/8a8a85c1f45979e1215f2a30bcfb9475/raw/template.json"

def load_config():
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR)
    if os.path.exists(CONFIG_DIR):
        with open(CONFIG_DIR, "r") as f:
            return json.load(f)
    return {}

def save_config(key, value):
    config = load_config()
    config[key] = value
    with open(CONFIG_DIR, "w") as f:
        json.dump(config, f)

def get_project_type():
    if os.path.exists("package.json"):
        return "web"
    elif os.path.exists("requirements.txt") or os.path.exists("pyproject.toml"):
        return "ai"
    return "unknown"

def sync_logic():
    os.makedirs(CONFIG_DIR, exist_ok=True)
    try:
        response = requests.get(MANIFEST_URL, timeout=10)
        if response.status_code == 200:
            data = response.json()
            with open(MANIFEST_FILE, "w") as f:
                json.dump(data, f, indent=2)
            return data
    except:
        if os.path.exists(MANIFEST_FILE):
            with open(MANIFEST_FILE, "r") as f:
                return json.load(f)
    return {}

@app.command()
def sync():
    console.print("[bold blue]🌍 Syncing with Origins HQ...[/bold blue]")
    templates = sync_logic()
    table = Table(title=f"Synced {len(templates)} Blueprints")
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Type", style="magenta")
    for key, val in templates.items():
        table.add_row(key, val['name'], val['type'])
    console.print(table)

@app.command()
def clone(template_id: str = typer.Argument(None)):
    templates = sync_logic()
    if not template_id:
        for k, v in templates.items():
            console.print(f" • [cyan]{k}[/cyan]: {v['description']}")
        template_id = Prompt.ask("Select Template ID")

    if template_id not in templates:
        console.print("[red]Error: Template ID not found.[/red]")
        raise typer.Exit()

    repo_data = templates[template_id]
    client = Prompt.ask("Client Name")
    slug = client.lower().replace(" ", "_")
    
    # FORCE PATH: Always save into origins-cli/projects/
    target_dir = os.path.join(PROJECTS_DIR, slug)
    cached_path = os.path.join(CACHE_DIR, template_id)

    if not os.path.exists(cached_path):
        os.makedirs(CACHE_DIR, exist_ok=True)
        console.print(f"[dim]Downloading {template_id} to global cache...[/dim]")
        subprocess.run(["git", "clone", repo_data['url'], cached_path])
    
    if os.path.exists(target_dir):
        console.print(f"[red]Error: Project {slug} already exists in {PROJECTS_DIR}[/red]")
        raise typer.Exit()

    shutil.copytree(cached_path, target_dir, dirs_exist_ok=True, ignore=shutil.ignore_patterns(".git"))

    with open(os.path.join(target_dir, "origins.config.json"), "w") as f:
        json.dump({"client": client, "template": repo_data['name'], "type": repo_data['type']}, f, indent=2)

    console.print(Panel(
        f"Project Created Successfully!\n\n"
        f"📍 Location: [bold cyan]{target_dir}[/bold cyan]\n"
        f"🚀 Run: [white]cd {target_dir} && origins setup[/white]", 
        title="Origins Forge", 
        border_style="green"
    ))

@app.command()
def ask(question: str):
    config = load_config()
    api_key = config.get("openai_key")
    if not api_key:
        api_key = Prompt.ask("Enter OpenAI API Key")
        save_config("openai_key", api_key)

    client = OpenAI(api_key=api_key)
    with console.status("[bold green]Analyzing...[/bold green]"):
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "system", "content": "Senior DevOps helper. Concise code snippets."},
                      {"role": "user", "content": question}]
        )
        console.print(Panel(Markdown(response.choices[0].message.content), title="Origins AI"))

@app.command()
def start():
    ptype = get_project_type()
    if ptype == "web":
        os.system("npm run dev")
    elif ptype == "ai":
        os.system("uvicorn main:app --reload")

@app.command()
def ship(message: str = typer.Option("Update", "--msg", "-m")):
    subprocess.run(["git", "add", "."])
    subprocess.run(["git", "commit", "-m", message])
    subprocess.run(["git", "push", "origin", "main"])
    console.print("[bold green]✅ Shipped.[/bold green]")

@app.command()
def kill(port: int):
    try:
        result = subprocess.check_output(f"lsof -t -i:{port}", shell=True)
        pid = int(result.strip())
        if Confirm.ask(f"Kill process {pid} on port {port}?"):
            os.kill(pid, 9)
    except:
        console.print(f"[green]Port {port} is free.[/green]")

@app.command()
def list():
    projects = [d for d in os.listdir(PROJECTS_DIR) if os.path.isdir(os.path.join(PROJECTS_DIR, d))]
    table = Table(title="Origins Forge Projects")
    table.add_column("Project Name", style="cyan")
    for p in projects: table.add_row(p)
    console.print(table)

@app.command()
def nuke(name: str):
    target = os.path.join(PROJECTS_DIR, name)
    if os.path.exists(target) and Confirm.ask(f"Delete {name}?"):
        shutil.rmtree(target)
        console.print("💥 Nuked.")


@app.command()
def doctor():
    checks = {"Node": "node -v", "Python": "python3 --version", "Git": "git --version", "Docker": "docker -v"}
    for n, c in checks.items():
        try:
            v = subprocess.check_output(c, shell=True).decode().strip()
            console.print(f"✅ {n}: {v}")
        except: console.print(f"❌ {n}: Missing")
        
@app.command()
def deploy():
    ptype = get_project_type()
    if ptype == "web":
        console.print("🚀 Deploying to Vercel...")
        os.system("vercel --prod")
    else:
        console.print("🚀 Deploying to Render/Railway...")
        os.system("git push origin main")

@app.command()
def db(type: str = "postgres"):
    if type == "postgres":
        os.system("docker run --name origins-pg -e POSTGRES_PASSWORD=password -d -p 5432:5432 postgres")
    elif type == "redis":
        os.system("docker run --name origins-redis -d -p 6379:6379 redis")

@app.command()
def secret(length: int = 32):
    console.print(Panel(secrets.token_hex(length // 2), title="Secret Generated"))

@app.command()
def gen(name: str):
    ptype = get_project_type()
    if ptype == "web":
        path = f"src/components/{name}.tsx"
        os.makedirs("src/components", exist_ok=True)
        with open(path, "w") as f:
            f.write(f"export default function {name}() {{ return <div>{name}</div>; }}")
    elif ptype == "ai":
        path = f"src/routes/{name.lower()}.py"
        os.makedirs("src/routes", exist_ok=True)
        with open(path, "w") as f:
            f.write(f"from fastapi import APIRouter\nrouter = APIRouter()\n@router.get('/{name.lower()}')\ndef get(): return {{'msg': '{name}'}}")

@app.command()
def scrub():
    ptype = get_project_type()
    if ptype == "web":
        shutil.rmtree("node_modules", ignore_errors=True)
    elif ptype == "ai":
        os.system("find . -type d -name __pycache__ -exec rm -r {} +")
@app.command()
def setup():
    """🚀 Automatically detects project type, installs dependencies, and starts localhost."""
    console.print("✨ [bold]ORIGINS SMART SETUP[/bold] ✨")
    
    # 1. Detect Node.js
    if os.path.exists("package.json"):
        console.print("📦 [cyan]Detected Node.js/Next.js Project...[/cyan]")
        with console.status("[bold green]Installing dependencies via npm...[/bold green]"):
            subprocess.run("npm install", shell=True)
        console.print("🌐 [bold blue]Starting local server at http://localhost:3000[/bold blue]")
        subprocess.run("npm run dev", shell=True)
    
    # 2. Detect Python
    elif os.path.exists("requirements.txt") or os.path.exists("main.py"):
        console.print("🐍 [yellow]Detected Python/FastAPI Project...[/yellow]")
        
        # Virtual Env Setup
        if not os.path.exists("venv"):
            console.print("📁 Creating virtual environment...")
            subprocess.run(f"{sys.executable} -m venv venv", shell=True)

        # OS-Specific pathing
        is_win = platform.system() == "Windows"
        pip_path = ".\\venv\\Scripts\\pip" if is_win else "./venv/bin/pip"
        python_path = ".\\venv\\Scripts\\python" if is_win else "./venv/bin/python"

        with console.status("[bold green]Installing dependencies...[/bold green]"):
            subprocess.run(f"{pip_path} install -r requirements.txt", shell=True)
        
        console.print("🌐 [bold blue]Starting FastAPI server...[/bold blue]")
        subprocess.run(f"{python_path} -m uvicorn main:app --reload", shell=True)
    
    else:
        console.print("[red]❌ No project type detected. Missing package.json or requirements.txt.[/red]")
if __name__ == "__main__":
    app()
