{ config, pkgs, ... }:

{
  home.username = "a";
  home.homeDirectory = "/home/a";

  home.packages = with pkgs; [
    kdePackages.kate
  ];

  # Let Home Manager manage itself
  programs.home-manager.enable = true;

  # https://nixos.wiki/wiki/FAQ/When_do_I_update_stateVersion
  home.stateVersion = "25.11";
}
