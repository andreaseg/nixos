{ ... }:

{
  programs.bash = {
    enable = true;
    shellAliases = {
      vim = "nvim";
      icat = "kitty +kitten icat";
      cat = "bat --paging=never";
    };
    initExtra = ''
      if [[ "$(whoami)" == "a" && "$(hostname)" == "nixos" ]]; then
        PS1='\[\e[0m\]❯ '
      fi

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
