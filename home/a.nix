{ config, pkgs, ... }:

{
  imports = [
    ./hyprland.nix
    ./eww.nix
    ./shell.nix
    ./jisho
  ];

  home.username = "a";
  home.homeDirectory = "/home/a";

  home.packages = with pkgs; [
    kdePackages.kate
    google-chrome
    mpv
    pavucontrol
    nerd-fonts.symbols-only
    python3
    glow
  ];

  home.sessionVariables = {
    TERMINAL = "kitty";
  };

  programs.home-manager.enable = true;
  programs.kitty.enable = true;
  programs.git.enable = true;
  programs.jisho = {
    enable = true;
    wanikani.enable = true;
    anki.fields = {
      "Migaku Japanese CUSTOM STYLING" = "Target Word Simplified";
    };
  };

  home.stateVersion = "25.11";
}
