{ config, pkgs, ... }:

{
  environment.systemPackages = with pkgs; [
    anki-bin
  ];

  fonts.packages = with pkgs; [
    noto-fonts
    noto-fonts-cjk-sans
    noto-fonts-cjk-serif
    noto-fonts-color-emoji
  ];
}
