{ pkgs, ... }:

{
  home.packages = [
    (pkgs.writers.writePython3Bin "jisho"
      { libraries = with pkgs.python3Packages; [ requests rich ]; }
      ''
        import sys
        import requests
        from rich.console import Console
        from rich.panel import Panel
        from rich.text import Text


        def search(query):
            resp = requests.get(
                "https://jisho.org/api/v1/search/words",
                params={"keyword": query},
                timeout=10,
            )
            resp.raise_for_status()
            return resp.json().get("data", [])


        def render_entry(entry, console):
            japanese = entry.get("japanese", [{}])
            word = japanese[0].get("word", "")
            reading = japanese[0].get("reading", "")
            is_common = entry.get("is_common", False)
            jlpt = entry.get("jlpt", [])

            title = Text()
            if word:
                title.append(word, style="bold cyan")
                title.append("  ")
                title.append(reading, style="cyan")
            else:
                title.append(reading, style="bold cyan")

            badges = Text()
            if is_common:
                badges.append("● common", style="green")
            if jlpt:
                if is_common:
                    badges.append("  ")
                level = jlpt[0].replace("jlpt-", "").upper()
                badges.append(f"● {level}", style="yellow")

            body = Text()
            prev_pos_key = None
            for i, sense in enumerate(entry.get("senses", []), 1):
                pos = sense.get("parts_of_speech", [])
                defs = sense.get("english_definitions", [])
                info = sense.get("info", [])

                pos_key = tuple(pos)
                if pos_key != prev_pos_key:
                    if i > 1:
                        body.append("\n")
                    if pos:
                        body.append("  " + " · ".join(pos) + "\n", style="italic dim")
                    prev_pos_key = pos_key

                body.append(f"  {i}. ", style="bold white")
                body.append(", ".join(defs), style="white")
                if info:
                    body.append(f"  ({', '.join(info)})", style="dim")
                body.append("\n")

            content = Text.assemble(badges, "\n\n", body) if badges else body

            console.print(Panel(
                content,
                title=title,
                title_align="left",
                border_style="blue",
                padding=(0, 1),
            ))


        def main():
            if len(sys.argv) < 2:
                print("Usage: jisho <query>")
                sys.exit(1)

            query = " ".join(sys.argv[1:])
            console = Console()

            try:
                results = search(query)
            except requests.RequestException as e:
                console.print(f"[red]Request failed:[/red] {e}")
                sys.exit(1)

            if not results:
                console.print(f"[yellow]No results for '{query}'[/yellow]")
                sys.exit(0)

            for entry in results[:5]:
                render_entry(entry, console)
                console.print()


        main()
      ''
    )
  ];
}
