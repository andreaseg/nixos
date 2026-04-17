{ config, pkgs, ... }:

{
  imports = [
    ./hardware-configuration.nix
    ../../modules/razer.nix
    ../../modules/anki.nix
  ];

  # Bootloader
  boot.loader.systemd-boot.enable = true;
  boot.loader.efi.canTouchEfiVariables = true;

  # Networking
  networking.hostName = "nixos";
  networking.networkmanager.enable = true;

  # Locale and timezone
  time.timeZone = "Europe/Oslo";
  i18n.defaultLocale = "en_US.UTF-8";

  # Keyboard
  services.xserver.xkb = {
    layout = "no";
    variant = "winkeys";
  };
  console.keyMap = "no";

  # Desktop environment
  services.xserver.enable = true;
  services.displayManager.sddm.enable = true;
  services.desktopManager.plasma6.enable = true;

  # Audio
  services.pulseaudio.enable = false;
  security.rtkit.enable = true;
  services.pipewire = {
    enable = true;
    alsa.enable = true;
    alsa.support32Bit = true;
    pulse.enable = true;
  };

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

  # Packages
  nixpkgs.config.allowUnfree = true;

  environment.systemPackages = with pkgs; [
    htop
    neofetch
    neovim
    kitty
    google-chrome
    mpv
    claude-code
    git
  ];

  environment.sessionVariables = {
    TERMINAL = "kitty";
  };

  system.stateVersion = "25.11";
}
