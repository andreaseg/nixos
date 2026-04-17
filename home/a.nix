{ config, pkgs, ... }:

{
  imports = [
    ./hyprland.nix
  ];

  home.username = "a";
  home.homeDirectory = "/home/a";

  home.packages = with pkgs; [
    kdePackages.kate
    google-chrome
    mpv
    pavucontrol
    nerd-fonts.symbols-only
  ];

  home.sessionVariables = {
    TERMINAL = "kitty";
  };

  programs.home-manager.enable = true;

  programs.kitty.enable = true;

  programs.git.enable = true;

  programs.bash = {
    enable = true;
    shellAliases = {
      vim = "nvim";
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

  home.stateVersion = "25.11";
}
