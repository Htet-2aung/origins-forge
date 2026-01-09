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
import platform
import sys , time
from google import genai  
import questionary
from github import Github
from concurrent.futures import ThreadPoolExecutor
from google.genai import errors
from rich.panel import Panel

app = typer.Typer(help="Origins Intelligent Dev Tool v0.2.4")
console = Console()



HOME_DIR = os.path.expanduser("~")
PROJECTS_DIR = os.path.join(HOME_DIR, "origins-projects")
CONFIG_DIR = os.path.join(HOME_DIR, ".origins")
CLI_ROOT = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(CONFIG_DIR, "cache")
MANIFEST_FILE = os.path.join(CONFIG_DIR, "templates.json")
MANIFEST_URL = "https://gist.github.com/Htet-2aung/8a8a85c1f45979e1215f2a30bcfb9475/raw/template.json"
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json") 
CURRENT_VERSION = "0.2.4"
# Points to a raw text file on GitHub that just contains the version number (e.g., "4.0.2")
VERSION_URL = "https://raw.githubusercontent.com/Htet-2aung/origins-forge/main/version.txt"

if not os.path.exists(PROJECTS_DIR):
    os.makedirs(PROJECTS_DIR)
if not os.path.exists(CONFIG_DIR):
    os.makedirs(CONFIG_DIR)

def load_config():
    # Ensure the folder exists
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR)
    
    # 2. Check for the FILE, not the folder
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {} # Return empty if file is corrupted
    return {}

def save_config(key, value):
    config = load_config()
    config[key] = value
    # 3. Save to the FILE path
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)

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


app = typer.Typer(help="Origins Intelligent Dev Tool v0.2.3")
console = Console()

# --- PATHS ---
HOME_DIR = os.path.expanduser("~")
PROJECTS_DIR = os.path.join(HOME_DIR, "origins-projects")
CONFIG_DIR = os.path.join(HOME_DIR, ".origins")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

def load_config():
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR)
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            try:
                return json.load(f)
            except:
                return {}
    return {}

def save_config(key, value):
    config = load_config()
    config[key] = value
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)

# --- COMMANDS ---

@app.command()
def config(
    reset: bool = typer.Option(False, "--reset", help="Clear all saved settings."),
    show: bool = typer.Option(False, "--show", help="Show current configuration.")
):
    """⚙️ Manage Origins Forge configuration."""
    if reset:
        if Confirm.ask("[bold red]Reset all settings?[/bold red]"):
            if os.path.exists(CONFIG_FILE):
                os.remove(CONFIG_FILE)
            console.print("[green]Settings wiped.[/green]")
        return

    if show:
        cfg = load_config()
        table = Table(title="Origins Forge Config")
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="magenta")
        table.add_row("Projects Dir", PROJECTS_DIR)
        
        key = cfg.get("gemini_key", "Not Set")
        masked = f"{key[:8]}****" if len(key) > 8 else key
        table.add_row("Gemini API Key", masked)
        console.print(table)

@app.command()
def sync():
    """🌍 Sync with Origins HQ to download latest blueprints."""
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
    """🏗️ Clone proprietary blueprints with automated git scrubbing."""
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

def retry_generate(client, model_id, contents):
    """Handles 429 errors by waiting and retrying to stay within Free Tier limits."""
    for attempt in range(5):
        try:
            return client.models.generate_content(model=model_id, contents=contents)
        except errors.ClientError as e:
            if "429" in str(e):
                # Standard exponential backoff
                wait_time = 12 * (attempt + 1) 
                console.print(f"[yellow]⚠️  AI Engine Busy. Cooling down ({wait_time}s)...[/yellow]")
                time.sleep(wait_time)
            else:
                raise e
    raise Exception("Max retries exceeded. AI quota is fully exhausted.")

@app.command()
def build(
    prompt: str = typer.Argument(None, help="Describe the app you want to build"),
    wizard: bool = typer.Option(False, "--wizard", "-w", help="Launch interactive setup"),
    swarm: bool = typer.Option(False, "--swarm", "-s", help="Use parallel AI agents")
):
    """🚀 Origins Build: High-speed app generation with Quota Management."""
    config = load_config()
    gemini_key = config.get("gemini_key")
    if not gemini_key:
        gemini_key = Prompt.ask("🔑 Enter Gemini API Key")
        save_config("gemini_key", gemini_key)
        
    client = genai.Client(api_key=gemini_key)

    # --- 1. MODE SELECTION ---
    if wizard:
        answers = questionary.form(
            name=questionary.text("Project Name (slug):", default="origins-app"),
            stack=questionary.select("Framework:", choices=["FastAPI", "Next.js", "Flask"]),
            db=questionary.select("Database:", choices=["PostgreSQL", "MongoDB", "SQLite"]),
            features=questionary.checkbox("Include Features:", choices=["Docker", "Auth", "CI/CD"]),
        ).ask()
        project_name = answers['name']
        final_prompt = f"Build a {answers['stack']} app with {answers['db']}. Features: {', '.join(answers['features'])}"
    else:
        if not prompt:
            prompt = Prompt.ask("What would you like to build today?")
        project_name = Prompt.ask("Project Name", default="origins-ai-app")
        final_prompt = prompt

    target_dir = os.path.join(PROJECTS_DIR, project_name)
    os.makedirs(target_dir, exist_ok=True)

    # --- 2. EXECUTION ---
    if swarm:
        console.print(Panel(f"🐝 [bold magenta]Swarm Mode[/bold magenta]\nDeploying parallel agents...", border_style="magenta"))
        tasks = {
            "api/main.py": f"Core API entry point for {final_prompt}",
            "requirements.txt": f"Dependencies for {final_prompt}",
            "README.md": f"Professional documentation for {final_prompt}",
            ".gitignore": "Standard python and env gitignore"
        }

        def run_agent(file_path, task_prompt):
            full_path = os.path.join(target_dir, file_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            # Use retry logic to prevent swarm from crashing on 429
            res = retry_generate(client, 'gemini-3-flash-preview', task_prompt)
            with open(full_path, "w") as f:
                f.write(res.text.strip().replace("```python", "").replace("```", ""))

        with ThreadPoolExecutor(max_workers=2) as executor: # Keep workers low for Free Tier
            executor.map(lambda p: run_agent(p[0], p[1]), tasks.items())
    else:
        # NORMAL MODE
        with console.status("[bold cyan]Architecting...[/bold cyan]"):
            struct_res = retry_generate(client, 'gemini-3-flash-preview', f"Return ONLY a JSON list of files for: {final_prompt}")
            files = json.loads(struct_res.text.strip().replace("```json", "").replace("```", ""))

        for f_path in track(files, description="Writing files..."):
            full_path = os.path.join(target_dir, f_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            code_res = retry_generate(client, 'gemini-3-flash-preview', f"Write code for {f_path} in {final_prompt}")
            with open(full_path, "w") as f:
                f.write(code_res.text.strip())

    console.print(Panel(f"✅ Build Complete: {target_dir}", title="Origins Factory", border_style="green"))

    if Confirm.ask("Push to GitHub?"):
        ship_to_github(target_dir, project_name)

@app.command()
def ask(question: str):
    """🧠 Query the Origins AI (Gemini 3 Flash)"""
    cfg = load_config()
    api_key = cfg.get("gemini_key")
    
    if not api_key:
        api_key = Prompt.ask("🔑 Enter Gemini API Key")
        save_config("gemini_key", api_key)

    try:
        client = genai.Client(api_key=api_key)
        
        with console.status("[bold green]Gemini 3 is thinking...[/bold green]"):
            # Use the exact ID from your debug-ai list
            response = client.models.generate_content(
                model='gemini-3-flash-preview', 
                contents=question
            )
            
            console.print(Panel(
                Markdown(response.text), 
                title="Origins AI (Gemini 3 Flash)", 
                border_style="cyan"
            ))
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")

@app.command()
def preview():
    """🚀 Launch a temporary cloud preview environment."""
    console.print("[bold blue]📦 Packaging ephemeral environment...[/bold blue]")
    # Example for a web project using Vercel
    subprocess.run(["vercel", "deploy", "--preview"], check=True)
    console.print("[bold green]✅ Preview live at: https://preview-link-here.com[/bold green]")
import subprocess
from github import Github

def ship_to_github(target_dir: str, repo_name: str):
    """🛠️ Automates local git init and remote push to GitHub."""
    config = load_config()
    gh_token = config.get("github_token")
    
    if not gh_token:
        console.print("[yellow]GitHub token not found. Skipping remote push.[/yellow]")
        return

    try:
        # 1. Create Remote Repo via PyGithub
        with console.status("[bold blue]Creating GitHub repository...[/bold blue]"):
            g = Github(gh_token)
            user = g.get_user()
            repo = user.create_repo(repo_name, private=True)
        
        # 2. Local Git Operations
        with console.status("[bold green]Pushing code to GitHub...[/bold green]"):
            # Initialize local repo
            subprocess.run(["git", "init"], cwd=target_dir, check=True, capture_output=True)
            
            # Add all files (including hidden ones)
            subprocess.run(["git", "add", "."], cwd=target_dir, check=True, capture_output=True)
            
            # Initial Commit
            subprocess.run(["git", "commit", "-m", "🚀 Initial build by Origins Forge"], cwd=target_dir, check=True, capture_output=True)
            
            # Branch setup (Modern standard is 'main')
            subprocess.run(["git", "branch", "-M", "main"], cwd=target_dir, check=True, capture_output=True)
            
            # Add remote using the token for seamless auth
            # Syntax: https://<token>@github.com/<user>/<repo>.git
            remote_url = repo.clone_url.replace("https://", f"https://{gh_token}@")
            subprocess.run(["git", "remote", "add", "origin", remote_url], cwd=target_dir, check=True, capture_output=True)
            
            # Push to main
            subprocess.run(["git", "push", "-u", "origin", "main"], cwd=target_dir, check=True, capture_output=True)

        console.print(f"\n[bold green]✅ Project successfully shipped![/bold green]")
        console.print(f"🔗 View it here: [link={repo.html_url}]{repo.html_url}[/link]\n")

    except Exception as e:
        console.print(f"[bold red]❌ GitHub Sync Failed:[/bold red] {e}")

@app.command()
def debug_ai():
    """🔍 List all models available to your API key."""
    cfg = load_config()
    client = genai.Client(api_key=cfg.get("gemini_key"))
    table = Table(title="Available AI Models")
    table.add_column("Model Name", style="cyan")
    
    for m in client.models.list():
        table.add_row(m.name)
    
    console.print(table)
REPO_NAME = "Htet-2aung/origins-forge"

def get_latest_version():
    """Fetch the latest tag from GitHub Releases."""
    try:
        # Using the GitHub API to check the latest release tag
        api_url = f"https://api.github.com/repos/{REPO_NAME}/releases/latest"
        response = requests.get(api_url, timeout=2)
        if response.status_code == 200:
            return response.json().get("tag_name", "").replace("v", "")
    except:
        return None
    return None

@app.command()
def update():
    """🔄 Industrial Update: Syncs source code and repairs environment."""
    console.print(Panel(f"🚀 [bold blue]Origins Forge Update System[/bold blue]\nCurrent Version: [cyan]{CURRENT_VERSION}[/cyan]"))
    
    # 1. Version Check
    latest = get_latest_version()
    if latest and latest == CURRENT_VERSION:
        console.print("[green]✅ You are already on the latest version.[/green]")
        if not Confirm.ask("Would you like to force a re-installation anyway?"):
            return
    elif latest:
        console.print(f"[yellow]🔔 New version [bold]{latest}[/bold] available! (Current: {CURRENT_VERSION})[/yellow]")

    # 2. Locate Root (Finds .git folder)
    current_file_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = current_file_dir
    while repo_root != "/" and not os.path.exists(os.path.join(repo_root, ".git")):
        repo_root = os.path.dirname(repo_root)

    if not os.path.exists(os.path.join(repo_root, ".git")):
        console.print("[bold red]❌ Error:[/bold red] CLI source not found. Are you running from a compiled .pkg?")
        console.print("[dim]For .pkg installs, please download the latest installer from GitHub Releases.[/dim]")
        return

    try:
        # 3. Pull Latest Code
        with console.status("[bold green]Pulling changes from GitHub...[/bold green]"):
            subprocess.run(["git", "pull", "origin", "main"], cwd=repo_root, check=True, capture_output=True)
        
        # 4. Bootstrap Build Tools
        # This fixes the 'setuptools' error by ensuring they exist in the venv
        with console.status("[bold yellow]Repairing build environment...[/bold yellow]"):
            subprocess.run([sys.executable, "-m", "pip", "install", "setuptools", "wheel"], check=True, capture_output=True)

        # 5. Re-install in Editable Mode
        with console.status("[bold cyan]Re-linking Origins CLI...[/bold cyan]"):
            # Target the folder containing pyproject.toml
            install_path = os.path.join(repo_root, "origins-cli") if "origins-cli" in os.listdir(repo_root) else repo_root
            subprocess.run([
                sys.executable, "-m", "pip", "install", "-e", install_path, "--no-build-isolation"
            ], check=True, capture_output=True)
            
        console.print(Panel("✨ [bold green]Update Successful![/bold green]\nOrigins Forge is now ready for action.", border_style="green"))
        
    except Exception as e:
        console.print(Panel(f"[bold red]Update Failed[/bold red]\n\n{str(e)}", title="System Error", border_style="red"))
@app.command()
def where():
    """📍 Locate all Origins Engine directories and binaries."""
    table = Table(title="Origins Engine Location Map", show_header=True, header_style="bold magenta")
    table.add_column("Component", style="cyan")
    table.add_column("Path", style="green")

    # Binary Location
    bin_path = shutil.which("origins") or "Not Found (Run within venv)"
    table.add_row("Executable Binary", bin_path)

    # Configuration Location
    table.add_row("Global Config", CONFIG_FILE)
    
    # Projects Location
    table.add_row("Software Factory", PROJECTS_DIR)

    # Source Code (Only visible during dev)
    try:
        source_dir = os.path.dirname(os.path.abspath(__file__))
        table.add_row("Source Code", source_dir)
    except:
        pass

    console.print(table)
    console.print(f"\n[dim]To open the config folder, run:[/dim] [bold]open {CONFIG_DIR}[/bold]")

@app.command()
def test_api():
    """🧪 Stress test AI & GitHub connectivity."""
    console.print(Panel("⚡ [bold]Starting Engine Stress Test[/bold]", border_style="yellow"))
    cfg = load_config()
    
    # 1. Gemini 3 Flash Test
    key = cfg.get("gemini_key")
    if key:
        try:
            client = genai.Client(api_key=key)
            with console.status("[bold cyan]Pinging Gemini 3 Flash...[/bold]"):
                start = time.time()
                # A simple lightweight prompt to test latency
                client.models.generate_content(model='gemini-3-flash-preview', contents="Say 'Ready'")
                elapsed = round(time.time() - start, 2)
            console.print(f"✅ [bold green]AI ENGINE:[/bold] Connected. Latency: {elapsed}s")
        except Exception as e:
            console.print(f"❌ [bold red]AI ENGINE:[/bold] Error: {str(e)[:50]}...")
    
    # 2. GitHub API Test
    token = cfg.get("github_token")
    if token:
        try:
            g = Github(token)
            user = g.get_user().login
            console.print(f"✅ [bold green]GITHUB API:[/bold] Authenticated as @{user}")
        except Exception:
            console.print("❌ [bold red]GITHUB API:[/bold] Authentication Failed.")
    else:
        console.print("⚠️  [bold yellow]GITHUB API:[/bold] No token found. Run 'origins config' to add one.")
@app.command()
def bootstrap():
    """🚀 One-click environment setup for new Origins engineers."""
    deps = ["git", "node", "python", "docker"]
    for d in deps:
        subprocess.run([sys.executable, "-m", "origins", "get", d])

@app.command()
def start():
    """🚀 Quick Start: Launch local server based on project type."""
    ptype = get_project_type()
    if ptype == "web":
        os.system("npm run dev")
    elif ptype == "ai":
        os.system("uvicorn main:app --reload")
@app.command()
def get(item: str = typer.Argument(..., help="Item to install (git, node, python, etc.)")):
    """📥 Universal Downloader: Auto-detects OS and installs dependencies."""
    
    registry = {
        "git": {"brew": "git", "winget": "Git.Git", "apt": "git"},
        "node": {"brew": "node", "winget": "OpenJS.NodeJS", "apt": "nodejs"},
        "python": {"brew": "python@3.12", "winget": "Python.Python.3.12", "apt": "python3"},
        "docker": {"brew": "docker", "winget": "Docker.DockerDesktop", "apt": "docker.io"},
    }

    item = item.lower()
    os_type = platform.system().lower() # 'windows', 'darwin' (mac), or 'linux'

    if item not in registry:
        console.print(f"[red]Item '{item}' not found in registry.[/red]")
        return

    commands = registry[item]

    try:
        if os_type == "darwin":  # macOS
            with console.status(f"🍎 [bold]MacOS:[/bold] Installing {item} via Brew..."):
                subprocess.run(["brew", "install", commands["brew"]], check=True)
        
        elif os_type == "windows":
            with console.status(f"🪟 [bold]Windows:[/bold] Installing {item} via Winget..."):
                # --silent --accept-source-agreements makes it industrial/non-interactive
                subprocess.run(["winget", "install", "--id", commands["winget"], "--silent", "--accept-source-agreements"], check=True)
        
        elif os_type == "linux":
            with console.status(f"🐧 [bold]Linux:[/bold] Installing {item} via APT..."):
                subprocess.run(["sudo", "apt-get", "update"], check=True, capture_output=True)
                subprocess.run(["sudo", "apt-get", "install", "-y", commands["apt"]], check=True)

        console.print(f"✅ [bold green]{item.upper()} installed successfully on {os_type.capitalize()}![/bold green]")
    
    except Exception as e:
        console.print(f"[bold red]❌ Installation failed:[/bold red] Ensure your system package manager is configured.")

@app.command()
def ship(message: str = typer.Option("Update", "--msg", "-m")):
    """🚢 Quick Ship: Commit and push all changes to GitHub."""
    subprocess.run(["git", "add", "."])
    subprocess.run(["git", "commit", "-m", message])
    subprocess.run(["git", "push", "origin", "main"])
    console.print("[bold green]✅ Shipped.[/bold green]")

@app.command()
def kill(port: int):
    """💀 Kill process running on specified port."""
    try:
        result = subprocess.check_output(f"lsof -t -i:{port}", shell=True)
        pid = int(result.strip())
        if Confirm.ask(f"Kill process {pid} on port {port}?"):
            os.kill(pid, 9)
    except:
        console.print(f"[green]Port {port} is free.[/green]")

@app.command()
def list():
    """📂 List all Origins Forge projects."""
    projects = [d for d in os.listdir(PROJECTS_DIR) if os.path.isdir(os.path.join(PROJECTS_DIR, d))]
    table = Table(title="Origins Forge Projects")
    table.add_column("Project Name", style="cyan")
    for p in projects: table.add_row(p)
    console.print(table)

@app.command()
def version():
    """🔢 Check current version and look for updates."""
    console.print(f"[bold]Origins Forge v{CURRENT_VERSION}[/bold]")
    
    try:
        response = requests.get(VERSION_URL, timeout=3)
        if response.status_code == 200:
            latest_version = response.text.strip()
            if latest_version != CURRENT_VERSION:
                console.print(Panel(
                    f"✨ [bold green]New Update Available: {latest_version}[/bold green]\n"
                    f"Run [bold cyan]origins update[/bold cyan] to get the latest features.",
                    border_style="orange1"
                ))
            else:
                console.print("[green]✅ You are running the latest version.[/green]")
    except Exception:
        console.print("[yellow]⚠️  Could not reach update server. Check your connection.[/yellow]")

@app.command()
def nuke(name: str):
    """💥 Nuke an Origins Forge project permanently."""
    target = os.path.join(PROJECTS_DIR, name)
    if os.path.exists(target) and Confirm.ask(f"Delete {name}?"):
        shutil.rmtree(target)
        console.print("💥 Nuked.")


@app.command()
def doctor():
    """🩺 Origins Doctor: Diagnose common environment issues."""
    checks = {"Node": "node -v", "Python": "python3 --version", "Git": "git --version", "Docker": "docker -v"}
    for n, c in checks.items():
        try:
            v = subprocess.check_output(c, shell=True).decode().strip()
            console.print(f"✅ {n}: {v}")
        except: console.print(f"❌ {n}: Missing")

@app.command()
def deploy():
    """🚀 One-Click Deploy: Push your project to the cloud."""
    ptype = get_project_type()
    if ptype == "web":
        console.print("🚀 Deploying to Vercel...")
        os.system("vercel --prod")
    else:
        console.print("🚀 Deploying to Render/Railway...")
        os.system("git push origin main")

@app.command()

def db(type: str = "postgres"):
    """🗄️ Launch local database instances via Docker."""
    if type == "postgres":
        os.system("docker run --name origins-pg -e POSTGRES_PASSWORD=password -d -p 5432:5432 postgres")
    elif type == "redis":
        os.system("docker run --name origins-redis -d -p 6379:6379 redis")

@app.command()
def secret(length: int = 32):
    """🔐 Generate a secure random secret key."""
    console.print(Panel(secrets.token_hex(length // 2), title="Secret Generated"))

@app.command()
def gen(name: str):
    """🛠️ Scaffold basic components/routes based on project type."""
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
    """🧹 Clean up project dependencies and cache files."""
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
