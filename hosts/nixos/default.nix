{ config, pkgs, ... }:

let
  sddmTheme = (pkgs.sddm-astronaut.override {
    themeConfig = {
      Background         = "Backgrounds/wallpaper.jpg";
      Font               = "Fira Code";
      RoundCorners       = "10";
      HeaderText         = "";
      DimBackground      = "0.2";
      CropBackground     = "true";
      PartialBlur        = "true";
      Blur               = "1.5";
      BlurMax            = "48";
      HaveFormBackground = "false";
      FormPosition       = "center";
      HideVirtualKeyboard = "true";
      # Kanagawa Wave palette
      FormBackgroundColor              = "#1F1F28";
      BackgroundColor                  = "#1F1F28";
      DimBackgroundColor               = "#1F1F28";
      HeaderTextColor                  = "#DCD7BA";
      DateTextColor                    = "#DCD7BA";
      TimeTextColor                    = "#DCD7BA";
      LoginFieldBackgroundColor        = "#2A2A37";
      PasswordFieldBackgroundColor     = "#2A2A37";
      LoginFieldTextColor              = "#DCD7BA";
      PasswordFieldTextColor           = "#DCD7BA";
      PlaceholderTextColor             = "#727169";
      UserIconColor                    = "#5D767D";
      PasswordIconColor                = "#5D767D";
      WarningColor                     = "#2A2A37";
      LoginButtonTextColor             = "#1F1F28";
      LoginButtonBackgroundColor       = "#5D767D";
      SystemButtonsIconsColor          = "#DCD7BA";
      SessionButtonTextColor           = "#DCD7BA";
      DropdownTextColor                = "#DCD7BA";
      DropdownBackgroundColor          = "#1F1F28";
      DropdownSelectedBackgroundColor  = "#2D4F67";
      HighlightTextColor               = "#DCD7BA";
      HighlightBackgroundColor         = "#2D4F67";
      HighlightBorderColor             = "#5D767D";
      HoverUserIconColor               = "#E58950";
      HoverPasswordIconColor           = "#E58950";
      HoverSystemButtonsIconsColor     = "#E58950";
      HoverSessionButtonTextColor      = "#E58950";
    };
  }).overrideAttrs (old: {
    installPhase = old.installPhase + ''
      chmod u+w $out/share/sddm/themes/sddm-astronaut-theme/Backgrounds
      ln -s /etc/sddm/wallpaper.jpg \
        $out/share/sddm/themes/sddm-astronaut-theme/Backgrounds/wallpaper.jpg
    '';
  });
in

{
  imports = [
    ./hardware-configuration.nix
    ../../modules/razer.nix
    ../../modules/anki.nix
  ];

  # Nix settings
  nix.settings.experimental-features = [ "nix-command" "flakes" ];

  # Bootloader
  boot.loader.systemd-boot.enable = true;
  boot.loader.efi.canTouchEfiVariables = true;

  # Networking
  networking.hostName = "nixos";
  networking.networkmanager.enable = true;

  # Locale and timezone
  time.timeZone = "Europe/Oslo";
  i18n.defaultLocale = "en_US.UTF-8";

  # Japanese input (Mozc via Fcitx5)
  i18n.inputMethod = {
    enable = true;
    type = "fcitx5";
    fcitx5.addons = with pkgs; [
      fcitx5-mozc
      fcitx5-gtk
    ];
  };

  # Keyboard
  services.xserver.xkb = {
    layout = "no";
    variant = "winkeys";
  };
  console.keyMap = "no";

  # Desktop environment
  services.xserver.enable = true;
  services.displayManager.sddm.enable = true;
  services.displayManager.sddm.wayland.enable = true;
  services.displayManager.sddm.theme = "sddm-astronaut-theme";

  # NVIDIA
  services.xserver.videoDrivers = [ "nvidia" ];
  hardware.nvidia = {
    modesetting.enable = true;
    open = false;
    nvidiaSettings = true;
    package = config.boot.kernelPackages.nvidiaPackages.stable;
  };

  # Hyprland
  programs.hyprland.enable = true;

  # Audio
  services.pulseaudio.enable = false;
  security.rtkit.enable = true;
  services.pipewire = {
    enable = true;
    alsa.enable = true;
    alsa.support32Bit = true;
    pulse.enable = true;
  };

  # Auto-unlock GNOME Keyring on SDDM login (allows NetworkManager to access WiFi credentials)
  security.pam.services.sddm.enableGnomeKeyring = true;
  services.gnome.gnome-keyring.enable = true;

  # Point SDDM theme background to the user's wallpaper at runtime
  systemd.tmpfiles.rules = [
    "L+ /etc/sddm/wallpaper.jpg - - - - /home/a/Wallpapers/wallhaven-d8e373.jpg"
  ];

  # Services
  services.printing.enable = true;
  services.flatpak.enable = true;

  # User account
  users.users.a = {
    isNormalUser = true;
    description = "A";
    extraGroups = [ "networkmanager" "wheel" ];
  };

  # Programs
  programs.firefox.enable = true;

  programs.neovim = {
    enable = true;
    defaultEditor = true;
  };

  # Fonts
  fonts.packages = with pkgs; [
    noto-fonts
    sarasa-gothic
    fira-code
  ];

  # Packages
  nixpkgs.config.allowUnfree = true;

  environment.systemPackages = with pkgs; [
    htop
    claude-code
    sddmTheme
  ];

  system.stateVersion = "25.11";
}
