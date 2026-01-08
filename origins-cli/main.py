import typer
import os
import shutil
import subprocess
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.progress import track

app = typer.Typer(help="Origins Intelligent Dev Tool")
console = Console()

# --- CONFIGURATION ---
TEMPLATES = {
    "web-mvp": "https://github.com/H212/admin-panel",
    "landing": "https://github.com/Htet-2aung/portfolio",
}

# --- HELPER: CONTEXT DETECTOR ---
def get_project_type():
    """Smartly detects if we are in a Web (Node) or AI (Python) project"""
    if os.path.exists("package.json"):
        return "web"
    elif os.path.exists("requirements.txt") or os.path.exists("pyproject.toml"):
        return "ai"
    return "unknown"

# --- COMMANDS ---

@app.command()
def clone(template_name: str = typer.Argument(None)):
    """🚀 Clones a blueprint and sets up a new client project."""
    if not template_name:
        console.print("[bold orange1]Available Blueprints:[/bold orange1]")
        for k, v in TEMPLATES.items():
            console.print(f" • [cyan]{k}[/cyan]")
        template_name = Prompt.ask("Select Blueprint")

    client = Prompt.ask("Client Name (e.g. Sony)")
    slug = client.lower().replace(" ", "_")
    
    console.print(f"[green]⚙️ Forging {slug}...[/green]")
    # Simulation of git clone
    subprocess.run(["git", "clone", TEMPLATES.get(template_name, ""), slug], 
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # Smart Setup
    console.print("[dim]🎨 Whitelabeling source code...[/dim]")
    shutil.rmtree(f"{slug}/.git", ignore_errors=True)
    
    console.print(Panel(f"Project Ready: [bold]./{slug}[/bold]\nRun: cd {slug} && origins start", title="Success", border_style="green"))

@app.command()
def start():
    """▶️ Auto-detects project type and runs the dev server."""
    ptype = get_project_type()
    
    if ptype == "web":
        console.print("[cyan]Detected Next.js/React. Starting npm...[/cyan]")
        os.system("npm run dev")
    elif ptype == "ai":
        console.print("[yellow]Detected Python/FastAPI. Starting uvicorn...[/yellow]")
        os.system("uvicorn main:app --reload")
    else:
        console.print("[red]❌ Unknown project type. No package.json or requirements.txt found.[/red]")

@app.command()
def ship(message: str = typer.Option("Update", "--msg", "-m")):
    """🚢 Automates the Git add/commit/push workflow."""
    console.print("[bold blue]⚓ Preparing to ship code...[/bold blue]")
    
    # 1. Check Status
    status = subprocess.getoutput("git status --porcelain")
    if not status:
        console.print("[yellow]No changes to ship.[/yellow]")
        raise typer.Exit()
    
    # 2. Add & Commit
    subprocess.run(["git", "add", "."])
    subprocess.run(["git", "commit", "-m", message])
    
    # 3. Push
    console.print("[dim]🚀 Pushing to origin/main...[/dim]")
    subprocess.run(["git", "push", "origin", "main"])
    
    console.print("[bold green]✅ Shipped![/bold green]")

@app.command()
def scrub():
    """🧹 Nukes node_modules or pycache to free space."""
    ptype = get_project_type()
    
    if ptype == "web":
        if Confirm.ask("Delete node_modules?"):
            shutil.rmtree("node_modules", ignore_errors=True)
            console.print("[green]🗑️ Cleaned node_modules[/green]")
    elif ptype == "ai":
        if Confirm.ask("Delete __pycache__ and venv?"):
            os.system("find . -type d -name __pycache__ -exec rm -r {} +")
            console.print("[green]🗑️ Cleaned Python cache[/green]")
    else:
        console.print("[red]Not inside a recognizable project.[/red]")

@app.command()
def gen(name: str):
    """⚡ Generates a Component (Web) or Route (AI) based on context."""
    ptype = get_project_type()
    
    if ptype == "web":
        # Create React Component
        path = f"src/components/{name}.tsx"
        os.makedirs("src/components", exist_ok=True)
        with open(path, "w") as f:
            f.write(f"export default function {name}()