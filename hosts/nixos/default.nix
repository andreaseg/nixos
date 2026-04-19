{ config, pkgs, ... }:

let
  sddmTheme = pkgs.where-is-my-sddm-theme.override {
    themeConfig.General = {
      backgroundFill        = "#1F1F28";
      font                  = "Fira Code";
      helpFont              = "Fira Code";
      basicTextColor        = "#DCD7BA";
      passwordTextColor     = "#DCD7BA";
      passwordCursorColor   = "#E58950";
      passwordInputBackground = "#2A2A37";
      passwordInputRadius   = "10";
      passwordInputWidth    = "0.3";
      passwordFontSize      = "24";
      showSessionsByDefault = "false";
      showUsersByDefault    = "false";
    };
  };
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
  services.displayManager.sddm.theme = "where_is_my_sddm_theme";
  services.displayManager.sddm.extraPackages = with pkgs.qt6; [ qt5compat qtsvg ];

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
