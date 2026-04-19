{ ... }:

{
  programs.bash = {
    enable = true;
    shellAliases = {
      vim = "nvim";
      icat = "kitty +kitten icat";
      cat = "bat --paging=never";
      screenshot = "mkdir -p ~/Pictures/Screenshots && grim -g \"$(slurp)\" ~/Pictures/Screenshots/$(date +%Y%m%d_%H%M%S).jpg";
    };
    initExtra = ''
      if [[ "$(whoami)" == "a" && "$(hostname)" == "nixos" ]]; then
        PS1='\[\e[38;2;114;113;105m\]\w \[\e[38;2;152;187;108m\]❯\[\e[0m\] '
      fi

      o() {
        case "$1" in
          *.md) mdcat "$1" ;;
          *)
            case $(file --mime-type -b "$1") in
              image/*)         kitty +kitten icat "$1" ;;
              video/*)         mpv "$1" ;;
              text/html)       firefox "$1" ;;
              application/pdf) zathura "$1" ;;
              text/*)          bat "$1" ;;
              *)               xdg-open "$1" ;;
            esac
            ;;
        esac
      }

      nrs() {
        if ! git -C ~/nixos-config diff --quiet || ! git -C ~/nixos-config diff --cached --quiet; then
          echo "Uncommitted changes in ~/nixos-config — aborting rebuild."
          return 1
        fi
        sudo nixos-rebuild switch --flake ~/nixos-config#nixos
      }
    '';
  };
}
