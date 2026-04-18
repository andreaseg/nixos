{ pkgs, ... }:

{
  home.packages = [
    (pkgs.writers.writePython3Bin "jisho"
      { libraries = with pkgs.python3Packages; [ requests rich ]; }
      ''
        import os
        import sys
        import requests
        from pathlib import Path
        from rich.console import Console
        from rich.panel import Panel
        from rich.text import Text

        WANIKANI_TOKEN_FILE = Path.home() / ".config" / "wanikani" / "token"
        WANIKANI_API = "https://api.wanikani.com/v2"


        def get_wanikani_token():
            token = os.environ.get("WANIKANI_API_TOKEN")
            if token:
                return token.strip()
            if WANIKANI_TOKEN_FILE.exists():
                return WANIKANI_TOKEN_FILE.read_text().strip()
            return None


        def search_jisho(query):
            resp = requests.get(
                "https://jisho.org/api/v1/search/words",
                params={"keyword": query},
                timeout=10,
            )
            resp.raise_for_status()
            return resp.json().get("data", [])


        def search_wanikani(query, token):
            resp = requests.get(
                f"{WANIKANI_API}/subjects",
                params={"types": "vocabulary,kanji", "slugs": query},
                headers={"Authorization": f"Bearer {token}"},
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json().get("data", [])
            return data[0] if data else None


        def is_exact_match(entry, query):
            for j in entry.get("japanese", []):
                if j.get("word") == query or j.get("reading") == query:
                    return True
            return False


        def render_entry(entry, console, wk_subject=None):
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
            if wk_subject:
                wk_level = wk_subject["data"].get("level", "?")
                badges.append(f"⬡ WaniKani L{wk_level}", style="bold magenta")
                badges.append("  ")
            if is_common:
                badges.append("● common", style="green")
            if jlpt:
                if is_common:
                    badges.append("  ")
                jlpt_str = jlpt[0].replace("jlpt-", "").upper()
                badges.append(f"● {jlpt_str}", style="yellow")

            body = Text()
            if wk_subject:
                wk_data = wk_subject["data"]
                meanings = [m["meaning"] for m in wk_data.get("meanings", [])]
                readings = [r["reading"] for r in wk_data.get("readings", [])]
                body.append("  Meanings: ", style="italic dim")
                body.append(", ".join(meanings) + "\n", style="white")
                if readings:
                    body.append("  Readings: ", style="italic dim")
                    body.append(", ".join(readings) + "\n", style="white")
            else:
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
                            pos_label = "  " + " · ".join(pos) + "\n"
                            body.append(pos_label, style="italic dim")
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
                border_style="magenta" if wk_subject else "blue",
                padding=(0, 1),
            ))


        def main():
            if len(sys.argv) < 2:
                print("Usage: jisho <query>")
                sys.exit(1)

            query = " ".join(sys.argv[1:])
            console = Console(force_terminal=True)
            token = get_wanikani_token()

            try:
                results = search_jisho(query)
            except requests.RequestException as e:
                console.print(f"[red]Request failed:[/red] {e}")
                sys.exit(1)

            if not results:
                console.print(f"[yellow]No results for '{query}'[/yellow]")
                sys.exit(0)

            exact = [e for e in results if is_exact_match(e, query)]
            to_show = exact if exact else results[:5]

            wk_subject = None
            if token and exact:
                try:
                    jisho_reading = (
                        exact[0].get("japanese", [{}])[0].get("reading", "")
                    )
                    wk_candidate = search_wanikani(query, token)
                    if wk_candidate:
                        wk_readings = [
                            r["reading"]
                            for r in wk_candidate["data"].get("readings", [])
                        ]
                        if jisho_reading in wk_readings:
                            wk_subject = wk_candidate
                except requests.RequestException:
                    pass

            for entry in to_show:
                render_entry(entry, console, wk_subject=wk_subject)
                console.print()


        main()
      ''
    )
  ];
}
