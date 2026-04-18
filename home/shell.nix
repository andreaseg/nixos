{ ... }:

{
  programs.bash = {
    enable = true;
    shellAliases = {
      vim = "nvim";
      icat = "kitty +kitten icat";
    };
    initExtra = ''
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
