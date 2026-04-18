{ config, pkgs, ... }:

{
  imports = [
    ./hyprland.nix
    ./eww.nix
    ./shell.nix
    ./jisho.nix
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

  home.stateVersion = "25.11";
}
